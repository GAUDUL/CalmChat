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
    ):
        last = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .first()
        )

        base_emotion = last.emotion_score if last else 50
        base_energy = last.energy_score if last else 50

        # 이전 누적 점수 + 이번 발화 변화량 + 자연 감소 반영.
        new_emotion = base_emotion + emotion_delta - self.EMOTION_DECAY
        new_energy = base_energy + energy_delta - self.ENERGY_DECAY

        # Mood 화면용 0~100 범위 고정.
        new_emotion = max(0, min(100, new_emotion))
        new_energy = max(0, min(100, new_energy))

        record = MetricRecord(
            user_id=user_id,
            emotion_score=new_emotion,
            energy_score=new_energy,
            # 건강 위험 맥락 감지 시 안전 안내 우선.
            health_keyword_flag=health_keyword_flag,
        )

        db.add(record)
        db.commit()

        return record
