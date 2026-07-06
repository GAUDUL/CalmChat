import base64
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import CareInterventionState, Conversation, FamilyVoice
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
# 같은 risk_level에 대해 케어 가이던스를 재전달하기까지의 최소 간격
# risk_level이 "올라가는 전이"는 이 쿨다운과 무관하게 항상 즉시 전달
INTERVENTION_COOLDOWN = timedelta(minutes=180)


def higher_risk(left: str, right: str) -> str:
    return left if RISK_ORDER.get(left, 0) >= RISK_ORDER.get(right, 0) else right


def _signal_confirmation(text: str, current_signal: dict, signal_kind: str) -> bool:
    matched_keywords = current_signal.get("matched_keywords", {}).get(signal_kind, [])
    if not matched_keywords:
        return False

    confidence = current_signal.get("danger_confidence_by_signal", {}).get(
        signal_kind,
        current_signal.get("danger_confidence"),
    )
    if confidence == "high":
        return True
    if confidence != "ambiguous":
        return False

    return llm_service.confirm_danger_signal(text, matched_keywords) is True


def current_safety_guidance(text: str, current_signal: dict) -> dict:
    if not (current_signal["crisis_keyword_flag"] or current_signal["health_keyword_flag"]):
        return {
            "risk_level": "normal",
            "feedback_actions": [],
            "health_keyword_flag_override": None,
            "crisis_keyword_flag_override": None,
        }

    crisis_confirmed = (
        _signal_confirmation(text, current_signal, "crisis")
        if current_signal["crisis_keyword_flag"]
        else False
    )
    health_confirmed = (
        _signal_confirmation(text, current_signal, "health")
        if current_signal["health_keyword_flag"]
        else False
    )

    risk_level = "danger" if crisis_confirmed or health_confirmed else "warning"
    actions = []
    if crisis_confirmed:
        actions.append("Encourage immediate caregiver or emergency support contact.")
    elif current_signal["crisis_keyword_flag"]:
        actions.append("Ask one calm clarification question before escalating.")

    if health_confirmed:
        actions.append("Encourage immediate caregiver or medical support contact.")
    elif current_signal["health_keyword_flag"]:
        actions.append("Ask one calm clarification question about the symptom severity.")

    actions.append("Keep the reply calm, short, and direct.")

    return {
        "risk_level": risk_level,
        "feedback_actions": actions,
        "health_keyword_flag_override": health_confirmed if current_signal["health_keyword_flag"] else None,
        "crisis_keyword_flag_override": crisis_confirmed if current_signal["crisis_keyword_flag"] else None,
    }


def _get_or_create_intervention_state(db: Session, user_id: int) -> CareInterventionState:
    state = db.query(CareInterventionState).filter_by(user_id=user_id).first()
    if state is None:
        state = CareInterventionState(user_id=user_id, last_risk_level="normal")
        db.add(state)
        db.flush()  # commit은 이후 대화 저장 시점에 한 번에
    return state


def _should_deliver_intervention(state: CareInterventionState, risk_level: str) -> bool:
    """
    가이던스를 이번 턴에 실제로 전달할지 결정
    - anomaly_service의 hysteresis는 "판정 결과"만 담당하고
      "이미 전달했는가"는 여기서 상태로 명시적으로 관리
    """
    if risk_level == "danger":
        return True  # 안전 문제는 쿨다운 없이 항상 전달

    if risk_level == "normal":
        return False

    previous_level = state.last_risk_level or "normal"
    if RISK_ORDER.get(risk_level, 0) > RISK_ORDER.get(previous_level, 0):
        return True  # 위험도가 새로 악화된 전이 시점 -> 항상 전달

    if state.last_intervention_risk_level != risk_level:
        return True  # 이 레벨로는 아직 한 번도 전달한 적 없음

    if state.last_intervention_at is None:
        return True

    last_at = state.last_intervention_at
    if last_at.tzinfo is None:
        last_at = last_at.replace(tzinfo=timezone.utc)

    return (datetime.now(timezone.utc) - last_at) >= INTERVENTION_COOLDOWN


def _update_intervention_state(state: CareInterventionState, risk_level: str, delivered: bool) -> None:
    state.last_risk_level = risk_level
    if delivered and risk_level != "normal":
        state.last_intervention_risk_level = risk_level
        state.last_intervention_at = datetime.now(timezone.utc)


def build_anomaly_system_prompt(anomaly_result: dict, deliver_intervention: bool) -> str | None:
    risk_level = anomaly_result.get("risk_level", "normal")
    if risk_level == "normal":
        return None

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

    if not deliver_intervention:
        # 이미 이 위험도에 대해 최근에 케어 액션을 전달했을 경우, 새 제안을 강요하지 않고
        # 그냥 평소처럼 따뜻하게 대화를 이어가되, 배경으로만 어조에 반영
        return (
            f"{llm_service.default_system_prompt()}\n\n"
            "[Internal care guidance]\n"
            f"Risk level: {risk_level} (already acknowledged recently)\n"
            "You already gave supportive guidance for this recently. Do not repeat a specific "
            "suggestion again. Just respond naturally to whatever the user is currently talking "
            "about, keeping a warm and attentive tone."
        )

    actions = anomaly_result.get("feedback_actions", [])
    action_block = "\n".join(f"- {action}" for action in actions)

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
        
    risk_level = anomaly_result.get("risk_level", "normal")
    intervention_state = _get_or_create_intervention_state(db, user_id)
    deliver_intervention = _should_deliver_intervention(intervention_state, risk_level)
    system_prompt = build_anomaly_system_prompt(anomaly_result, deliver_intervention)

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
    # 이번 턴에 실제로 무엇을 전달했는지 명시적으로 기록 (다음 턴이 텍스트를 추측하지 않도록)
    _update_intervention_state(intervention_state, risk_level, deliver_intervention)
    db.add(intervention_state)
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
        corrected_text = llm_service.correct_transcript(text)

        if not text:
            raise HTTPException(status_code=400, detail="Could not recognize speech.")

        # LLM을 통해 응답 생성
        response_text, context, safety_overrides = generate_chat_response(user_id, corrected_text, db)

        # 감정 분석 파이프라인
        background_tasks.add_task(
            run_emotion_pipeline,
            user_id,
            corrected_text,
            safety_overrides["health_keyword_flag_override"],
            safety_overrides["crisis_keyword_flag_override"],
        )

        voice_embedding_path  = None

        # 가족 음성 활성화 경우
        if user.family_voice_enabled:
            family_voice = db.query(FamilyVoice).filter(FamilyVoice.user_id == user_id).first()
            voice_embedding_path = family_voice.embedding_path if family_voice else None

        # TTS 수행
        audio_bytes = tts_service.synthesize(
            text=response_text,
            use_family_voice=user.family_voice_enabled,
            voice_embedding_path=voice_embedding_path ,
        )

        return VoiceChatResponse(
            text=corrected_text,
            confidence=stt_result.get("confidence"),
            response_text=response_text,
            used_context=context,
            audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
            audio_content_type="audio/mpeg",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)