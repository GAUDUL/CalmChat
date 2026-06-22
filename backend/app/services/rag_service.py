"""
RAG + 사용자 프로파일 문서 서비스.

흐름:
  1. 대화가 누적되면(또는 주기적으로 / profile/update 호출 시) 대화 이력을 LLM에 요약 요청
  2. 요약된 프로파일 문서를 MySQL(ProfileDocument)에 저장
  3. 동시에 벡터화하여 Chroma에 upsert -> 다음 대화 시 관련 컨텍스트 검색에 사용

RAG 인덱스 갱신 주기는 settings.rag_update_interval_minutes로 관리 (스케줄러는 별도 구현 필요 -
예: APScheduler 혹은 외부 cron이 /profile/update를 주기적으로 호출).
"""
import chromadb
from app.config import settings
from app.services.llm_service import llm_service


class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.collection = self.client.get_or_create_collection(settings.vector_db_collection)

    def get_relevant_context(self, user_id: int, query_text: str, top_k: int = None) -> list:
        top_k = top_k or settings.rag_top_k
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where={"user_id": str(user_id)},
        )
        docs = results.get("documents", [[]])[0]
        return docs

    def upsert_profile_document(self, user_id: int, content: str):
        self.collection.upsert(
            ids=[f"profile_{user_id}"],
            documents=[content],
            metadatas=[{"user_id": str(user_id), "type": "profile"}],
        )

    def regenerate_profile_from_history(self, user_id: int, conversation_texts: list) -> str:
        """대화 이력을 LLM으로 요약해 사용자 프로파일 문서를 새로 생성."""
        joined = "\n".join(conversation_texts[-50:])  # 최근 N개만 사용 (토큰 절약)
        summary_prompt = (
            "다음은 한 노인 사용자의 최근 대화 기록입니다. "
            "이 사용자의 성격, 관심사, 건강/정서 상태, 자주 언급하는 가족/지인, "
            "선호하는 대화 주제를 5줄 이내로 요약해 주세요.\n\n"
            f"{joined}"
        )
        summary = llm_service.generate_response(user_text=summary_prompt, context=[])
        self.upsert_profile_document(user_id, summary)
        return summary


rag_service = RAGService()
