from .engine import EmotionEngine
from .state_service import EmotionStateService


engine = EmotionEngine()
state_service = EmotionStateService()


def process_message(db, user_id: int, text: str):

    delta = engine.extract(text)

    record = state_service.update(
        db=db,
        user_id=user_id,
        emotion_delta=delta["emotion_delta"],
        energy_delta=delta["energy_delta"],
        # 건강 위험 맥락 저장.
        health_keyword_flag=delta["health_keyword_flag"],
    )

    return record
