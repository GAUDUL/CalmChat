import base64
import os
import shutil
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Conversation, FamilyVoice
from app.routers.users import require_user_access
from app.schemas.schemas import ChatRequest, ChatResponse, ConversationResponse, VoiceChatResponse
from app.services.emotion.worker import run_emotion_pipeline
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_HISTORY_LIMIT = 80


def generate_chat_response(user_id: int, text: str, db: Session):
    context = rag_service.get_relevant_context(db, user_id, text)
    packed_context = "\n\n".join(context)

    response_text = llm_service.generate_response(
        user_text=text,
        context=[packed_context]
    )

    user_message = Conversation(
        user_id=user_id,
        role="user",
        content=text,
    )

    assistant_message = Conversation(
        user_id=user_id,
        role="assistant",
        content=response_text,
    )

    db.add(user_message)
    db.add(assistant_message)
    db.commit()

    db.refresh(user_message)
    db.refresh(assistant_message)

    # 추가
    rag_service.add_conversation(
        user_message.id,
        user_id,
        "user",
        text,
    )

    rag_service.add_conversation(
        assistant_message.id,
        user_id,
        "assistant",
        response_text,
    )

    return response_text, context



@router.get("/history/{user_id}", response_model=list[ConversationResponse])
def get_chat_history(
    user_id: int,
    limit: int = CHAT_HISTORY_LIMIT,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    require_user_access(db, user_id, x_device_key)

    limit = max(1, min(limit, CHAT_HISTORY_LIMIT))

    records = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )

    return list(reversed(records))


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    require_user_access(db, payload.user_id, x_device_key)

    response_text, context = generate_chat_response(payload.user_id, payload.text, db)

    background_tasks.add_task(run_emotion_pipeline, payload.user_id, payload.text)

    return ChatResponse(response_text=response_text, used_context=context)



# 음성 기반 채팅 메시지를 처리하는 API 엔드포인트.
# 사용자 ID와 오디오 파일을 받아 STT를 통해 텍스트로 변환하고,
# 챗봇 응답을 생성한 후 TTS를 통해 음성으로 변환하여 반환
@router.post("/audio", response_model=VoiceChatResponse)
def voice_chat(
    background_tasks: BackgroundTasks,
    user_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    # 사용자 접근 권한 확인
    user = require_user_access(db, user_id, x_device_key)
    tmp_path = None

    try:
        # 업로드된 오디오 파일을 임시 파일로 저리
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        # STT 수행
        stt_result = stt_service.transcribe(tmp_path)
        text = stt_result.get("text", "").strip()

        if not text:
            raise HTTPException(status_code=400, detail="Could not recognize speech.")

        # LLM을 통해 응답 생성
        response_text, context = generate_chat_response(user_id, text, db)
        # 감정 분석 파이프라인
        background_tasks.add_task(run_emotion_pipeline, user_id, text)

        voice_model_id = None
        # 가족 음성 활성화 경우
        # 해당 사용자의 가족 음성 모델 ID 조회
        if user.family_voice_enabled:
            family_voice = db.query(FamilyVoice).filter(FamilyVoice.user_id == user_id).first()
            voice_model_id = family_voice.voice_id if family_voice else None

        # TTS 수행
        audio_bytes = tts_service.synthesize(
            text=response_text,
            use_family_voice=user.family_voice_enabled,
            voice_model_id=voice_model_id,
        )

        return VoiceChatResponse(
            text=text,
            confidence=stt_result.get("confidence"),
            response_text=response_text,
            used_context=context,
            audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
            audio_content_type="audio/mpeg",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
