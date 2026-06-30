import re
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
        # assistant의 짧은 응답(인삿말 등)은 노이즈라 제외
        if role == "assistant":
            if any(x in content.lower() for x in ["hello", "hi there", "good to hear"]):
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

    def get_relevant_context(
        self,
        db: Session,
        user_id: int,
        query_text: str,
        top_k: int | None = None,
    ):
        """
        LLM에게 넘길 "컨텍스트 묶음" 생성

        구성:
        1) 사용자 프로필 (장기 기억)
        2) 최근 관련 대화 (단기 기억)
        """
        top_k = top_k or settings.rag_top_k

        # 프로필(장기 기억) 가져오기
        profile = self._query_profile_documents(user_id, query_text, 1)

        # 대화 기반 RAG 검색 (단기 기억)
        conversations = self._query_conversations(user_id, query_text, top_k)

        context = []

        if profile:
            context.append("[PROFILE]")
            context.append(profile[0])

        if conversations:
            context.append("[MEMORY]")
            context.extend(conversations)

        return context
    
    def _query_conversations(self, user_id: int, query_text: str, top_k: int):
        
        results = self.conversation_collection.query(
            query_texts=[query_text],
            n_results=top_k * 3,  # 후보군 확대
            where={"user_id": str(user_id)},
            include=["documents", "metadatas", "distances"] # 거리 정보 포함
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored_items = []

        for i, doc in enumerate(docs):
            if not doc or len(doc.strip()) < 5:
                continue

            if len(doc.strip()) < 10:
                continue

            meta = metas[i] if i < len(metas) else {}

            # 실제 거리를 기반으로 한 유사도 점수 (0~1 사이로 정규화 필요)
            # ChromaDB의 distance는 낮을수록 유사도가 높으므로, 1에서 빼서 유사도 점수로 변환
            actual_distance = distances[i] if i < len(distances) else 1.0 # 기본값 설정
            similarity_score = max(0, 1.0 - actual_distance)

            # 설정된 최소 점수 미달 시 스킵
            if similarity_score < settings.rag_min_score:
                continue

            # time decay
            created_at = meta.get("created_at")
            time_score = self._time_decay_score_from_meta(created_at)

            # role weight (중요: user > assistant)
            role = meta.get("role", "")
            role_weight = 1.2 if role == "user" else 0.8

            # length penalty (너무 짧은 답변 제거 효과)
            length_weight = min(len(doc) / 50, 1.0)

            # final score
            final_score = (
                0.6 * similarity_score +
                0.3 * time_score +
                0.1 * role_weight
            )

            scored_items.append((final_score, doc))

        scored_items.sort(key=lambda x: x[0], reverse=True)

        return [doc for _, doc in scored_items[:top_k]]

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
        
        return math.exp(-settings.rag_time_decay_alpha * (age_hours / 24))


rag_service = RAGService()
