import json
import logging

from .engine import EmotionEngine
from .state_service import EmotionStateService


logger = logging.getLogger(__name__)
engine = EmotionEngine()
state_service = EmotionStateService()

# engine.py의 CRISIS_EMOTION_PENALTY(-8)를 정확히 상쇄하기 위한 값.
# 두 상수가 어긋나면 override 로직이 오작동하므로 값을 바꿀 땐 engine.py와 함께 맞출 것.
CRISIS_OVERRIDE_COMPENSATION = 8


def process_message(
    db,
    user_id: int,
    text: str,
    health_keyword_flag_override: bool | None = None,
    crisis_keyword_flag_override: bool | None = None,
    precomputed_signal: dict | None = None,
):
    signal = precomputed_signal if precomputed_signal is not None else engine.extract(text)

    health_keyword_flag = (
        signal["health_keyword_flag"]
        if health_keyword_flag_override is None
        else health_keyword_flag_override
    )
    crisis_keyword_flag = (
        signal["crisis_keyword_flag"]
        if crisis_keyword_flag_override is None
        else crisis_keyword_flag_override
    )

    emotion_delta = signal["emotion_delta"]

    # engine.py는 crisis_keyword_flag가 True일 때 emotion_delta에 -8을 이미
    # 반영해뒀다. 이후 LLM 확인으로 crisis가 False로 뒤집히면(override), 그
    # -8을 정확히 상쇄해야 "crisis 아님"으로 확정된 경우와 점수가 맞아떨어진다.
    if signal["crisis_keyword_flag"] and crisis_keyword_flag_override is False:
        emotion_delta += CRISIS_OVERRIDE_COMPENSATION

    logger.info(
        "emotion_extraction=%s",
        json.dumps(
            {
                "user_id": user_id,
                "emotion_delta": emotion_delta,
                "health_keyword_flag": health_keyword_flag,
                "crisis_keyword_flag": crisis_keyword_flag,
                "raw_health_keyword_flag": signal["health_keyword_flag"],
                "raw_crisis_keyword_flag": signal["crisis_keyword_flag"],
                "danger_confidence": signal.get("danger_confidence"),
                "danger_confidence_by_signal": signal.get("danger_confidence_by_signal", {}),
                "matched_keywords": signal.get("matched_keywords", {}),
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    return state_service.update(
        db=db,
        user_id=user_id,
        emotion_delta=emotion_delta,
        health_keyword_flag=health_keyword_flag,
        crisis_keyword_flag=crisis_keyword_flag,
    )
