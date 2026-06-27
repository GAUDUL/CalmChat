import base64
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, UploadFile, BackgroundTasks   
from sqlalchemy.orm import Session


from app.database import get_db
from app.models.db_models import Conversation, FamilyVoice
from app.routers.users import get_user_or_404
from app.schemas.schemas import ChatRequest, ChatResponse, ConversationResponse, VoiceChatResponse
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.emotion.worker import run_emotion_pipeline

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_HISTORY_LIMIT = 80

# 사용자 입력을 기반으로 RAG 검색 → LLM 응답 생성 → 대화 내역 저장
def generate_chat_response(user_id: int, text: str, db: Session):
    get_user_or_404(db, user_id)

    context = rag_service.get_relevant_context(user_id, text)
    response_text = llm_service.generate_response(text, context)

    db.add(Conversation(user_id=user_id, role="user", content=text))
    db.add(Conversation(user_id=user_id, role="assistant", content=response_text))
    db.commit()

    return response_text, context


# 응답 텍스트를 음성으로 변환 (가족 음성 사용 여부 포함)
def synthesize_response_audio(user_id: int, text: str, db: Session) -> bytes:
    user = get_user_or_404(db, user_id)
    voice_model_id = None

    if user.family_voice_enabled:
        family_voice = (
            db.query(FamilyVoice)
            .filter(FamilyVoice.user_id == user_id)
            .first()
        )
        voice_model_id = family_voice.voice_model_id if family_voice else None

    return tts_service.synthesize(
        text=text,
        use_family_voice=user.family_voice_enabled,
        voice_model_id=voice_model_id,
    )


@router.get("/history/{user_id}", response_model=list[ConversationResponse])
async def get_chat_history(user_id: int, limit: int = CHAT_HISTORY_LIMIT, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)

    limit = max(1, min(limit, CHAT_HISTORY_LIMIT))

    records = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )

    # 화면 표시용 시간순 정렬.
    return list(reversed(records))


# 텍스트 채팅 API
# 사용자 텍스트 입력을 받아 AI 응답 반환
# 테스트용
@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    response_text, context = generate_chat_response(payload.user_id, payload.text, db)

    background_tasks.add_task(
        run_emotion_pipeline,
        payload.user_id,
        payload.text
    )

    return ChatResponse(response_text=response_text, used_context=context)


# 음성 채팅 API
# 음성 업로드 → STT → AI 응답 생성 → TTS → 결과 반환
@router.post("/audio", response_model=VoiceChatResponse)
async def voice_chat(
    background_tasks: BackgroundTasks,
    user_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        # STT
        stt_result = stt_service.transcribe(tmp_path)
        text = stt_result.get("text", "")
        # LLM
        response_text, context = generate_chat_response(user_id, text, db)

        background_tasks.add_task(
            run_emotion_pipeline,
            user_id,
            text
        )
        
        # TTS
        audio_bytes = synthesize_response_audio(user_id, response_text, db)

        return VoiceChatResponse(
            text=text,
            confidence=stt_result.get("confidence"),
            response_text=response_text,
            used_context=context,
            audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
            audio_content_type="audio/wav",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
