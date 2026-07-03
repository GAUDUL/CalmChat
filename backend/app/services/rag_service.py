import re
import hashlib
import tiktoken
from collections import Counter

import chromadb
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import math

from app.config import settings
from app.models.db_models import Conversation
from app.services.llm_service import llm_service


class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        # 사용자 장기 기억(프로필) 저장 컬렉션
        self.profile_collection = self.client.get_or_create_collection(
            settings.vector_db_profile_collection
        )
        # 사용자 대화 기억 저장 컬렉션
        self.conversation_collection = self.client.get_or_create_collection(
            settings.vector_db_conversation_collection
        )
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def add_conversation(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
    ):
        content = content.strip()
        # 너무 짧은 문장은 저장 X
        if len(content) < 5:
            return
        # assistant 짧은 응답은 저장 X
        if role == "assistant" and len(content) < 30:
            return
        # assistant의 특정 인사말은 저장 X
        if role == "assistant":
            if any(
                x in content.lower()
                for x in [
                    "hello",
                    "hi there",
                    "good to hear",
                ]
            ):
                return
        
        # ChromaDB에 저장
        # document: 실제 검색 대상 텍스트
        # metadata: 필터링용 정보(user_id 등)
        self.conversation_collection.upsert(
            ids=[f"conv_{conversation_id}"],
            documents=[f"{role}: {content}"],
            metadatas=[{
                "user_id": str(user_id),
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat()
            }]
        )

    # 텍스트 정규화
    def _normalize(self, text: str) -> str:
        text = re.sub(r"\[.*?\]", "", text)  # 태그 제거
        return re.sub(r"\s+", " ", text.strip().lower())
    # 텍스트 해시값 생성
    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
    # 텐스트 토큰 수 추정 및 반환
    def _estimate_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))
    # 토큰 제한에 맞춰 패킹
    def _pack_by_token_limit(self, texts, limit):
        result = []
        used = 0

        for t in texts:
            tokens = self._estimate_tokens(t)
            if used + tokens > limit:
                break
            result.append(t)
            used += tokens

        return result

    # 사용자 관련 컨텍스트 검색
    def get_relevant_context(
        self,
        db: Session,
        user_id: int,
        query_text: str,
        top_k: int | None = None,
    ):
        pair_limit = 4

        # 프로필(장기 기억) 가져오기
        profile = self._query_profile_documents(user_id, query_text, 1)

        # SQL 최근 대화 강제 포함
        recent_conversations = self._get_recent_conversations( db, user_id, limit=pair_limit,)
        # 최근 대화 토큰 수 계산
        recent_tokens = sum(self._estimate_tokens(x) for x in recent_conversations)
        rag_limit_tokens = max(settings.rag_max_context - recent_tokens, 0)
        # 대화 중복 방지용
        recent_set = {self._hash(x) for x in recent_conversations}

        adaptive_top_k = min(
            settings.rag_top_k,
            max(5, rag_limit_tokens // 50)
        )

        # 대화 기반 RAG 검색 (단기 기억)
        conversations = self._query_conversations(user_id, query_text, adaptive_top_k)
        # 최근 대화 중복 제외
        conversations = [
            doc for doc in conversations
             if self._hash(doc) not in recent_set
        ]
        
        context = []

        if profile:
            context.append("[PROFILE]")
            context.append(profile[0])

        if recent_conversations:
            context.append("[RECENT_MEMORY]")
            context.extend(recent_conversations)

        if conversations:
            context.append("[RELATED_MEMORY]")
            context.extend(
                self._pack_by_token_limit(conversations, rag_limit_tokens)
            )

        return context
    
    # 관련성 높은 대화 검색 (유사도, 시간 경과, 역할 가중치 적용)
    def _query_conversations(self, user_id: int, query_text: str, top_k: int):
        
        results = self.conversation_collection.query(
            query_texts=[query_text],
            n_results=top_k * 3,  # 후보군 확대
            where={"user_id": str(user_id)},
            include=["documents", "metadatas", "distances"] # 거리 정보 포함
        )
        # 문서, 메타데이터, 거리 정보 추출
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored_items = []

        for i, doc in enumerate(docs):
            # 너무 짧은 문장 제외
            if not doc or len(doc.strip()) < 5:
                continue

            meta = metas[i] if i < len(metas) else {}

            # 실제 거리를 기반으로 한 유사도 점수 (0~1 사이로 정규화)
            # ChromaDB의 distance는 낮을수록 유사도가 높으므로, 1에서 빼서 유사도 점수로 변환
            actual_distance = distances[i] if i < len(distances) else 1.0 # 기본값 설정
            similarity_score = max(0.0, 1.0 - actual_distance)
            
            # 설정된 최소 점수 미달 시 스킵
            if similarity_score < settings.rag_min_score:
                continue

            # time decay
            # 시간 경과에 따른 점수 계산
            created_at = meta.get("created_at")
            time_score = self._time_decay_score_from_meta(created_at)

            # role weight (중요도: user > assistant)
            # 역할에 따른 가중치 부여
            role = meta.get("role", "")
            role_weight = 1.2 if role == "user" else 0.8

            # final score (유사도 60%, 시간 30%, 역할 10% 가중치)
            final_score = (
                0.6 * similarity_score +
                0.3 * time_score +
                0.1 * role_weight
            )

            scored_items.append((final_score, doc))
        # 최종 점수 기준 내림차순 정렬
        scored_items.sort(key=lambda x: x[0], reverse=True)

        return [doc for _, doc in scored_items[:top_k]]
    
    # DB 에서 최근 대화 기록 가져옴
    # 대화 쌍 형태 구성 후 반환
    def _get_recent_conversations(self, db, user_id, limit=2):
        records = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit * 2) # 대화 쌍 구성할 수 있도록
            .all()
        )

        records = records[::-1] # 오래된 것 -> 최신 순으로

        pairs = []
        i = 0

        while i < len(records):
            if records[i].role == "user":
                chunk = records[i:i+2]
                formatted = "\n".join(
                    f"[{r.role.upper()}] {r.content}"
                    for r in chunk
                )
                pairs.append(formatted)
                i += len(chunk)
            else:
                i += 1

        return pairs

    # 사용자 프로필 문서
    def _query_profile_documents(self, user_id: int, query_text: str, top_k: int) -> list[str]:
        """
        사용자 장기 프로필 벡터 검색
        (성격 / 관심사 / 상태 요약)
        """
        results = self.profile_collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where={"user_id": str(user_id)},
        )
        return results.get("documents", [[]])[0]

    def _terms(self, text: str) -> Counter:
        """
        (현재 미사용)
        키워드 기반 간단 검색용 토큰화 함수
        - 나중에 hybrid RAG 할 때 사용 가능
        """
        tokens = re.findall(r"[0-9a-zA-Z가-힣]{2,}", text.lower())
        return Counter(tokens)

    def upsert_profile_document(self, user_id: int, content: str):
        """
        사용자 프로필 업데이트
        (LLM이 요약한 장기 기억 저장)
        """
        self.profile_collection.upsert(
            ids=[f"profile_{user_id}"],
            documents=[content],
            metadatas=[{"user_id": str(user_id), "type": "profile"}],
        )
        
    def regenerate_profile_from_history(self, user_id: int, conversation_texts: list[str]) -> str:
        """
        최근 대화를 LLM으로 요약해서
        사용자 프로필을 갱신하는 함수
        """
        # 최근 50개 대화만 사용 (토큰 제한 방지)
        joined = "\n".join(conversation_texts[-50:])
        # LLM 요약 프롬프트
        summary_prompt = (
            "Summarize this user's recent conversation history for future personalization. "
            "Include personality, interests, emotional or health patterns, family/support cues, "
            "and preferred conversation topics in five concise lines or fewer.\n\n"
            f"{joined}"
        )
         # LLM 호출 (요약 생성)
        summary = llm_service.generate_response(user_text=summary_prompt, context=[])
        # 프로필 벡터DB에 저장
        self.upsert_profile_document(user_id, summary)
        return summary
    
    # score 함수
    def _time_decay_score_from_meta(self, created_at_str: str | None) -> float:
        if not created_at_str:
            return 1.0

        try:
            created_at = datetime.fromisoformat(created_at_str)
        except Exception:
            return 1.0
        
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_hours = (now - created_at).total_seconds() / 3600
        # 지수 감쇠 함수 사용 -> 시간 감쇠 점수 계산
        return math.exp(-settings.rag_time_decay_alpha * (age_hours / 24))


rag_service = RAGService()
