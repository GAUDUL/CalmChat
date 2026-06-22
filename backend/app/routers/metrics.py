from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import MetricRecord
from app.schemas.schemas import MetricsResponse
from app.services.anomaly_service import anomaly_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/{user_id}", response_model=MetricsResponse)
async def get_metrics(user_id: int, db: Session = Depends(get_db)):
    """프론트: 수치 조회 -> GET /metrics -> 이상치 탐지 -> 수치 + 플래그 반환"""
    latest = (
        db.query(MetricRecord)
        .filter(MetricRecord.user_id == user_id)
        .order_by(MetricRecord.recorded_at.desc())
        .first()
    )
    anomaly_result = anomaly_service.detect(db, user_id)

    return MetricsResponse(
        user_id=user_id,
        emotion_score=latest.emotion_score if latest else None,
        energy_score=latest.energy_score if latest else None,
        anomaly_detected=anomaly_result["anomaly_detected"],
        recommended_solution=anomaly_result["recommended_solution"],
    )
