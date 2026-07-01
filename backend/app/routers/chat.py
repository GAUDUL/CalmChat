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
from app.services.anomaly_service import RISK_ORDER, anomaly_service
from app.services.emotion.processor import engine as emotion_engine
from app.services.emotion.worker import run_emotion_pipeline
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_HISTORY_LIMIT = 80


def higher_risk(left: str, right: str) -> str:
    return left if RISK_ORDER.get(left, 0) >= RISK_ORDER.get(right, 0) else right


def current_safety_guidance(text: str, current_signal: dict) -> dict:
    matched_keywords = (
        current_signal.get("matched_keywords", {}).get("crisis", [])
        + current_signal.get("matched_keywords", {}).get("health", [])
    )
    if not (current_signal["crisis_keyword_flag"] or current_signal["health_keyword_flag"]):
        return {
            "risk_level": "normal",
            "feedback_actions": [],
            "health_keyword_flag_override": None,
            "crisis_keyword_flag_override": None,
        }

    signal_kind = "crisis" if current_signal["crisis_keyword_flag"] else "health"
    confirmed = True
    if current_signal.get("danger_confidence") == "ambiguous":
        confirmed = llm_service.confirm_danger_signal(text, matched_keywords)

    risk_level = "danger" if confirmed is True else "warning"
    is_danger = risk_level == "danger"

    if signal_kind == "crisis":
        actions = [
            "Encourage immediate caregiver or emergency support contact."
            if is_danger
            else "Ask one calm clarification question before escalating.",
            "Keep the reply calm, short, and direct.",
        ]
        return {
            "risk_level": risk_level,
            "feedback_actions": actions,
            "health_keyword_flag_override": False,
            "crisis_keyword_flag_override": is_danger,
        }

    actions = [
        "Encourage immediate caregiver or medical support contact."
        if is_danger
        else "Ask one calm clarification question about the symptom severity.",
        "Keep the reply calm, short, and direct.",
    ]
    return {
        "risk_level": risk_level,
        "feedback_actions": actions,
        "health_keyword_flag_override": is_danger,
        "crisis_keyword_flag_override": False,
    }


def build_anomaly_system_prompt(anomaly_result: dict) -> str | None:
    risk_level = anomaly_result.get("risk_level", "normal")
    if risk_level == "normal":
        return None

    actions = anomaly_result.get("feedback_actions", [])
    action_block = "\n".join(f"- {action}" for action in actions)

    guidance_by_level = {
        "caution": (
            "The user's recent mood or energy has shown a mild decline. "
            "Naturally suggest one gentle activity, such as a short walk, sunlight, "
            "or recalling a pleasant memory. Do not mention scores or anomaly detection."
        ),
        "warning": (
            "The user's recent mood or energy has shown a noticeable decline. "
            "Lead with empathy, then proactively suggest one supportive action such as "
            "listening to familiar music, taking a small rest, or contacting family. "
            "Do not sound alarming, and do not mention scores or anomaly detection."
        ),
        "danger": (
            "A health or safety risk signal has been detected. Respond calmly and directly. "
            "Encourage the user to contact a caregiver or emergency support now. "
            "Do not minimize the situation."
        ),
    }

    return (
        f"{llm_service.default_system_prompt()}\n\n"
        "[Internal care guidance]\n"
        f"Risk level: {risk_level}\n"
        f"{guidance_by_level.get(risk_level, '')}\n"
        "Use these service actions as private guidance, not as a visible checklist:\n"
        f"{action_block}"
    )


def generate_chat_response(user_id: int, text: str, db: Session):
    context = rag_service.get_relevant_context(db, user_id, text)
    packed_context = "\n\n".join(context)
    anomaly_result = anomaly_service.detect(db, user_id)
    current_signal = emotion_engine.extract(text)
    current_guidance = current_safety_guidance(text, current_signal)
    merged_risk_level = higher_risk(
        anomaly_result.get("risk_level", "normal"),
        current_guidance["risk_level"],
    )
    if current_guidance["risk_level"] != "normal":
        current_is_at_least_existing = (
            RISK_ORDER[current_guidance["risk_level"]]
            >= RISK_ORDER[anomaly_result.get("risk_level", "normal")]
        )
        anomaly_result = {
            **anomaly_result,
            "risk_level": merged_risk_level,
            "feedback_actions": (
                current_guidance["feedback_actions"]
                if current_is_at_least_existing
                else anomaly_result.get("feedback_actions", [])
            ),
        }
    system_prompt = build_anomaly_system_prompt(anomaly_result)

    response_text = llm_service.generate_response(
        user_text=text,
        context=[packed_context],
        system_prompt=system_prompt,
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

    return response_text, context, {
        "health_keyword_flag_override": current_guidance["health_keyword_flag_override"],
        "crisis_keyword_flag_override": current_guidance["crisis_keyword_flag_override"],
    }



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

    response_text, context, safety_overrides = generate_chat_response(payload.user_id, payload.text, db)

    background_tasks.add_task(
        run_emotion_pipeline,
        payload.user_id,
        payload.text,
        safety_overrides["health_keyword_flag_override"],
        safety_overrides["crisis_keyword_flag_override"],
    )

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
        response_text, context, safety_overrides = generate_chat_response(user_id, text, db)
        # 감정 분석 파이프라인
        background_tasks.add_task(
            run_emotion_pipeline,
            user_id,
            text,
            safety_overrides["health_keyword_flag_override"],
            safety_overrides["crisis_keyword_flag_override"],
        )

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
