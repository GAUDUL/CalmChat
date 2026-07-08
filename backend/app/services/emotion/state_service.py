from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord

DEFAULT_BASELINE_SCORE = 50.0


class EmotionStateService:
    """Persists one MetricRecord per turn.

    engine.py가 주는 emotion_delta는 "이번 turn 하나가 기존 점수에 미치는
    변화폭"이다. 직전 기록의 emotion_score에 이 delta를 더해 0~100 범위로
    클램프한 값을 새 turn의 절대 점수로 저장한다.

    energy_score는 더 이상 존재하지 않는다 (energy는 별도로 점수화하지 않기로
    확정됨). 트렌드/이상 감지(EMA, z-score 등)는 downstream의 anomaly_service가
    이 history를 대상으로 처리하므로, 여기서는 추가 스무딩/디케이를 적용하지 않는다.
    """

    def _last_score(self, db: Session, user_id: int) -> float:
        last = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .first()
        )
        if last is None or last.emotion_score is None:
            return DEFAULT_BASELINE_SCORE
        return last.emotion_score

    def update(
        self,
        db: Session,
        user_id: int,
        emotion_delta: float,
        health_keyword_flag: bool = False,
        crisis_keyword_flag: bool = False,
    ):
        new_score = self._last_score(db, user_id) + emotion_delta
        new_score = max(0.0, min(100.0, new_score))

        record = MetricRecord(
            user_id=user_id,
            emotion_score=new_score,
            health_keyword_flag=health_keyword_flag,
            crisis_keyword_flag=crisis_keyword_flag,
        )

        db.add(record)
        db.commit()

        return record