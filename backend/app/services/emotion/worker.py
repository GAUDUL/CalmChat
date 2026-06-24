from app.database import SessionLocal
from app.services.emotion.processor import process_message


def run_emotion_pipeline(user_id: int, text: str):
    db = SessionLocal() 
    try:
        process_message(db, user_id, text)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Emotion Pipeline Error] {e}")
    finally:
        db.close()