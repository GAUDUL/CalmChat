import json
import logging

from .engine import EmotionEngine
from .state_service import EmotionStateService


logger = logging.getLogger(__name__)
engine = EmotionEngine()
state_service = EmotionStateService()


def process_message(
    db,
    user_id: int,
    text: str,
    health_keyword_flag_override: bool | None = None,
    crisis_keyword_flag_override: bool | None = None,
):
    delta = engine.extract(text)
    health_keyword_flag = (
        delta["health_keyword_flag"]
        if health_keyword_flag_override is None
        else health_keyword_flag_override
    )
    crisis_keyword_flag = (
        delta["crisis_keyword_flag"]
        if crisis_keyword_flag_override is None
        else crisis_keyword_flag_override
    )
    emotion_delta = delta["emotion_delta"]
    energy_delta = delta["energy_delta"]
    if delta["crisis_keyword_flag"] and crisis_keyword_flag_override is False:
        emotion_delta += 8
        energy_delta += 4

    logger.info(
        "emotion_extraction=%s",
        json.dumps(
            {
                "user_id": user_id,
                "emotion_delta": emotion_delta,
                "energy_delta": energy_delta,
                "health_keyword_flag": health_keyword_flag,
                "crisis_keyword_flag": crisis_keyword_flag,
                "raw_health_keyword_flag": delta["health_keyword_flag"],
                "raw_crisis_keyword_flag": delta["crisis_keyword_flag"],
                "danger_confidence": delta.get("danger_confidence"),
                "matched_keywords": delta.get("matched_keywords", {}),
            },
            ensure_ascii=False,
            default=str,
        ),
    )

    return state_service.update(
        db=db,
        user_id=user_id,
        emotion_delta=emotion_delta,
        energy_delta=energy_delta,
        health_keyword_flag=health_keyword_flag,
        crisis_keyword_flag=crisis_keyword_flag,
    )
