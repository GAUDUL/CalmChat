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
        energy_delta=delta["energy_delta"]
    )

    return record