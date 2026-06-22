from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Conversation
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """프론트: 텍스트 전달 -> POST /chat -> LLM + RAG -> 응답 텍스트 반환"""
    context = rag_service.get_relevant_context(payload.user_id, payload.text)
    response_text = llm_service.generate_response(payload.text, context)

    db.add(Conversation(user_id=payload.user_id, role="user", content=payload.text))
    db.add(Conversation(user_id=payload.user_id, role="assistant", content=response_text))
    db.commit()

    return ChatResponse(response_text=response_text, used_context=context)
