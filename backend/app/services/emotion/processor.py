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
    signal = engine.extract(text)

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

    # NOTE: the old delta-based design nudged the score when a crisis flag was
    # raised but later overridden to false by the LLM confirmation step. In the
    # model-based design, emotion_score comes straight from the emotion model
    # and is intentionally independent of the crisis/health keyword signals,
    # so no compensation is needed here anymore.
    emotion_score = signal["emotion_score"]

    logger.info(
        "emotion_extraction=%s",
        json.dumps(
            {
                "user_id": user_id,
                "emotion_score": emotion_score,
                "dominant": signal.get("dominant"),
                "intensity": signal.get("intensity"),
                "positive_score": signal.get("positive_score"),
                "negative_score": signal.get("negative_score"),
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
        emotion_score=emotion_score,
        health_keyword_flag=health_keyword_flag,
        crisis_keyword_flag=crisis_keyword_flag,
    )