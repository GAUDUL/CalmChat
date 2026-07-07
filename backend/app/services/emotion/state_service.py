from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord


class EmotionStateService:
    """Persists one MetricRecord per turn.

    The previous version accumulated an `emotion_delta` on top of the last
    stored score with a manual decay constant (the "vitality score" design).
    Now that emotion scoring comes from the model as an absolute 0-100 reading
    per turn (see EmotionEngine._to_emotion_score), we just store that value
    directly. Trend/anomaly detection (EMA smoothing, baseline z-scores) is
    handled downstream by anomaly_service against the resulting history, so we
    deliberately avoid smoothing/decaying again here to prevent double
    smoothing.
    """

    def update(
        self,
        db: Session,
        user_id: int,
        emotion_score: float,
        health_keyword_flag: bool = False,
        crisis_keyword_flag: bool = False,
    ):
        record = MetricRecord(
            user_id=user_id,
            emotion_score=max(0.0, min(100.0, emotion_score)),
            health_keyword_flag=health_keyword_flag,
            crisis_keyword_flag=crisis_keyword_flag,
        )

        db.add(record)
        db.commit()

        return record