import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Conversation
from app.schemas.schemas import ChatRequest, ChatResponse, VoiceChatResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.stt_service import stt_service

router = APIRouter(prefix="/chat", tags=["Chat"])


def generate_chat_response(user_id: int, text: str, db: Session):
    context = rag_service.get_relevant_context(user_id, text)
    response_text = llm_service.generate_response(text, context)

    db.add(Conversation(user_id=user_id, role="user", content=text))
    db.add(Conversation(user_id=user_id, role="assistant", content=response_text))
    db.commit()

    return response_text, context


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    response_text, context = generate_chat_response(payload.user_id, payload.text, db)
    return ChatResponse(response_text=response_text, used_context=context)


@router.post("/audio", response_model=VoiceChatResponse)
async def voice_chat(
    user_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        stt_result = stt_service.transcribe(tmp_path)
        text = stt_result["text"]
        response_text, context = generate_chat_response(user_id, text, db)

        return VoiceChatResponse(
            text=text,
            confidence=stt_result.get("confidence"),
            response_text=response_text,
            used_context=context,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
