import numpy as np
from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord


LOW_EMOTION_THRESHOLD = 35
LOW_ENERGY_THRESHOLD = 35
DROP_FROM_RECENT_AVG_THRESHOLD = 5
Z_SCORE_THRESHOLD = 1.5

SOLUTION_MAP = {
    "crisis_keyword": "Immediate safety check recommended. Contact a trusted family member or emergency support.",
    "health_keyword": "Health warning detected. Consider contacting a caregiver or medical service.",
    "low_emotion": "Offer emotional support, gentle music, or a family call.",
    "low_energy": "Suggest a light activity, stretch, water, or rest check.",
}


class AnomalyService:
    def _is_low_or_dropping(self, scores: np.ndarray, low_threshold: float) -> bool:
        latest = scores[0]

        if latest <= low_threshold:
            return True

        if len(scores) < 3:
            return False

        recent_avg = scores[1:].mean()
        recent_std = scores[1:].std() + 1e-6
        drop_from_avg = recent_avg - latest
        z = (latest - recent_avg) / recent_std

        return drop_from_avg >= DROP_FROM_RECENT_AVG_THRESHOLD and z < -Z_SCORE_THRESHOLD

    def detect(self, db: Session, user_id: int, window: int = 14) -> dict:
        records = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .limit(window)
            .all()
        )
        if not records:
            return {"anomaly_detected": False, "recommended_solution": None}

        latest = records[0]
        if latest.crisis_keyword_flag:
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["crisis_keyword"]}

        if latest.health_keyword_flag:
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["health_keyword"]}

        emotion_scores = np.array([r.emotion_score for r in records if r.emotion_score is not None])
        energy_scores = np.array([r.energy_score for r in records if r.energy_score is not None])

        if len(emotion_scores) and self._is_low_or_dropping(emotion_scores, LOW_EMOTION_THRESHOLD):
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["low_emotion"]}

        if len(energy_scores) and self._is_low_or_dropping(energy_scores, LOW_ENERGY_THRESHOLD):
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["low_energy"]}

        return {"anomaly_detected": False, "recommended_solution": None}


anomaly_service = AnomalyService()
