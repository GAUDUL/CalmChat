import numpy as np
from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord


LOW_EMOTION_THRESHOLD = 35
LOW_ENERGY_THRESHOLD = 35
DROP_FROM_RECENT_AVG_THRESHOLD = 5
Z_SCORE_THRESHOLD = 1.5

SOLUTION_MAP = {
    "low_emotion": "정서 케어 콘텐츠 추천 (밝은 음악, 가족 전화 유도)",
    "low_energy": "신체 활동 권장 콘텐츠 추천 (가벼운 스트레칭 안내)",
    "health_keyword": "보호자 알림 + 병원 방문 안내",
}


class AnomalyService:
    def _is_low_or_dropping(self, scores: np.ndarray, low_threshold: float) -> bool:
        latest = scores[0]

        # 낮은 누적 점수 즉시 케어.
        if latest <= low_threshold:
            return True

        if len(scores) < 3:
            return False

        recent_avg = scores[1:].mean()
        recent_std = scores[1:].std() + 1e-6
        drop_from_avg = recent_avg - latest
        z = (latest - recent_avg) / recent_std

        # 절대 하락폭 + z-score 동시 확인.
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

        # 건강 위험 맥락 최우선.
        if records[0].health_keyword_flag:
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["health_keyword"]}

        emotion_scores = np.array([r.emotion_score for r in records if r.emotion_score is not None])
        energy_scores = np.array([r.energy_score for r in records if r.energy_score is not None])

        if len(emotion_scores) and self._is_low_or_dropping(emotion_scores, LOW_EMOTION_THRESHOLD):
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["low_emotion"]}

        if len(energy_scores) and self._is_low_or_dropping(energy_scores, LOW_ENERGY_THRESHOLD):
            return {"anomaly_detected": True, "recommended_solution": SOLUTION_MAP["low_energy"]}

        return {"anomaly_detected": False, "recommended_solution": None}


anomaly_service = AnomalyService()
