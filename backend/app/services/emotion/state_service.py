from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord


class EmotionStateService:
    EMOTION_DECAY = 0.1
    ENERGY_DECAY = 0.1

    def update(
        self,
        db: Session,
        user_id: int,
        emotion_delta: float,
        energy_delta: float,
        health_keyword_flag: bool = False,
        crisis_keyword_flag: bool = False,
    ):
        last = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .first()
        )

        base_emotion = last.emotion_score if last else 50
        base_energy = last.energy_score if last else 50

        new_emotion = base_emotion + emotion_delta - self.EMOTION_DECAY
        new_energy = base_energy + energy_delta - self.ENERGY_DECAY

        record = MetricRecord(
            user_id=user_id,
            emotion_score=max(0, min(100, new_emotion)),
            energy_score=max(0, min(100, new_energy)),
            health_keyword_flag=health_keyword_flag,
            crisis_keyword_flag=crisis_keyword_flag,
        )

        db.add(record)
        db.commit()

        return record
