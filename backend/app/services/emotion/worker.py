from app.database import SessionLocal
from app.services.emotion.processor import process_message


def run_emotion_pipeline(
    user_id: int,
    text: str,
    health_keyword_flag_override: bool | None = None,
    crisis_keyword_flag_override: bool | None = None,
    precomputed_signal: dict | None = None,
):
    db = SessionLocal() 
    try:
        process_message(
            db,
            user_id,
            text,
            health_keyword_flag_override=health_keyword_flag_override,
            crisis_keyword_flag_override=crisis_keyword_flag_override,
            precomputed_signal=precomputed_signal,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Emotion Pipeline Error] {e}")
    finally:
        db.close()
