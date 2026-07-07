from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.db_models import MetricRecord
from app.routers.users import require_user_access
from app.schemas.schemas import MetricsResponse
from app.services.anomaly_service import anomaly_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])

DEFAULT_EMOTION_SCORE = 50
seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)


@router.get("/{user_id}", response_model=MetricsResponse)
def get_metrics(
    user_id: int,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    require_user_access(db, user_id, x_device_key)

    latest = (
        db.query(MetricRecord)
        .filter(MetricRecord.user_id == user_id)
        .order_by(MetricRecord.recorded_at.desc())
        .first()
    )
    
    anomaly_result = anomaly_service.detect(db, user_id)

    records = (
        db.query(MetricRecord)
        .filter(
            MetricRecord.user_id == user_id,
            MetricRecord.recorded_at >= seven_days_ago,
        )
        .order_by(MetricRecord.recorded_at.asc())
        .all()
    )

    daily = defaultdict(list)

    for r in records:
        day = r.recorded_at.date()

        daily[day].append(
            {
                "emotion": r.emotion_score,
            }
        )

    weekly_trend = []

    for day, values in list(daily.items())[-7:]:
        emotion_values = [
            v["emotion"]
            for v in values
            if v["emotion"] is not None
        ]

        emotion_avg = (
            round(sum(emotion_values) / len(emotion_values), 1)
            if emotion_values
            else DEFAULT_EMOTION_SCORE
        )

        weekly_trend.append(
            {
                "date": day.isoformat(),
                "emotion_score": emotion_avg,
            }
        )

    return MetricsResponse(
        user_id=user_id,
        emotion_score=latest.emotion_score if latest else DEFAULT_EMOTION_SCORE,
        anomaly_detected=anomaly_result["anomaly_detected"],
        recommended_solution=anomaly_result["recommended_solution"],
        risk_level=anomaly_result["risk_level"],
        anomaly_types=anomaly_result["anomaly_types"],
        feedback_actions=anomaly_result["feedback_actions"],
        signals=anomaly_result["signals"],
        decision_log=anomaly_result["decision_log"],
        weekly_trend=weekly_trend,
    )
