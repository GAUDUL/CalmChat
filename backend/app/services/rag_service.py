import re
from collections import Counter

import chromadb
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db_models import Conversation
from app.services.llm_service import llm_service


class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.collection = self.client.get_or_create_collection(settings.vector_db_collection)

    def get_relevant_context(self, db: Session, user_id: int, query_text: str, top_k: int | None = None) -> list[str]:
        top_k = top_k or settings.rag_top_k
        docs = self._query_profile_documents(user_id, query_text, top_k)
        if docs:
            return docs

        # Fallback retrieval keeps chat contextual before the profile vector is built.
        return self._search_recent_conversations(db, user_id, query_text, top_k)

    def _query_profile_documents(self, user_id: int, query_text: str, top_k: int) -> list[str]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where={"user_id": str(user_id)},
        )
        return results.get("documents", [[]])[0]

    def _search_recent_conversations(
        self,
        db: Session,
        user_id: int,
        query_text: str,
        top_k: int,
        window: int = 80,
    ) -> list[str]:
        query_terms = self._terms(query_text)
        if not query_terms:
            return []

        records = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(window)
            .all()
        )

        scored = []
        for record in records:
            terms = self._terms(record.content or "")
            overlap = sum((terms & query_terms).values())
            if overlap:
                scored.append((overlap, record.created_at, f"{record.role}: {record.content}"))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [content for _, _, content in scored[:top_k]]

    def _terms(self, text: str) -> Counter:
        tokens = re.findall(r"[0-9a-zA-Z가-힣]{2,}", text.lower())
        return Counter(tokens)

    def upsert_profile_document(self, user_id: int, content: str):
        self.collection.upsert(
            ids=[f"profile_{user_id}"],
            documents=[content],
            metadatas=[{"user_id": str(user_id), "type": "profile"}],
        )

    def regenerate_profile_from_history(self, user_id: int, conversation_texts: list[str]) -> str:
        joined = "\n".join(conversation_texts[-50:])
        summary_prompt = (
            "Summarize this user's recent conversation history for future personalization. "
            "Include personality, interests, emotional or health patterns, family/support cues, "
            "and preferred conversation topics in five concise lines or fewer.\n\n"
            f"{joined}"
        )
        summary = llm_service.generate_response(user_text=summary_prompt, context=[])
        self.upsert_profile_document(user_id, summary)
        return summary


rag_service = RAGService()
