from sqlalchemy.orm import Session
from app.models.db_models import MetricRecord


class EmotionStateService:

    EMOTION_DECAY = 0.1
    ENERGY_DECAY = 0.1

    def update(self, db: Session, user_id: int, emotion_delta: float, energy_delta: float):

        last = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .first()
        )

        base_emotion = last.emotion_score if last else 50
        base_energy = last.energy_score if last else 50

        # 상태 업데이트
        new_emotion = base_emotion + emotion_delta - self.EMOTION_DECAY
        new_energy = base_energy + energy_delta - self.ENERGY_DECAY

        # clamp (중요)
        new_emotion = max(0, min(100, new_emotion))
        new_energy = max(0, min(100, new_energy))

        record = MetricRecord(
            user_id=user_id,
            emotion_score=new_emotion,
            energy_score=new_energy,
            health_keyword_flag=False
        )

        db.add(record)
        db.commit()

        return record