"""
이상치 탐지 모듈 (초기 버전).

현재 구현: 최근 N개의 emotion_score / energy_score에 대해 단순 이동평균 + z-score 기반 탐지.
수치화 방법론은 ⚠️ 팀 합의 필요 항목 -> 추후 시계열 모델(예: Prophet, LSTM, Isolation Forest 등)로
교체 가능하도록 detect() 인터페이스만 고정해 둠.
"""
import numpy as np
from sqlalchemy.orm import Session
from app.models.db_models import MetricRecord

Z_SCORE_THRESHOLD = 1.5
SOLUTION_MAP = {
    "low_emotion": "정서 케어 콘텐츠 추천 (밝은 음악, 가족 전화 유도)",
    "low_energy": "신체 활동 권장 콘텐츠 추천 (가벼운 스트레칭 안내)",
    "health_keyword": "보호자 알림 + 병원 방문 안내",
}


class AnomalyService:
    def detect(self, db: Session, user_id: int, window: int = 14) -> dict:
        records = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .limit(window)
            .all()
        )
        if len(records) < 3:
            return {"anomaly_detected": False, "recommended_solution": None}

        emotion_scores = np.array([r.emotion_score for r in records if r.emotion_score is not None])
        energy_scores = np.array([r.energy_score for r in records if r.energy_score is not None])

        anomaly = False
        solution = None

        if len(emotion_scores) > 2:
            z = (emotion_scores[0] - emotion_scores.mean()) / (emotion_scores.std() + 1e-6)
            if z < -Z_SCORE_THRESHOLD:
                anomaly = True
                solution = SOLUTION_MAP["low_emotion"]

        if len(energy_scores) > 2 and not anomaly:
            z = (energy_scores[0] - energy_scores.mean()) / (energy_scores.std() + 1e-6)
            if z < -Z_SCORE_THRESHOLD:
                anomaly = True
                solution = SOLUTION_MAP["low_energy"]

        if records[0].health_keyword_flag:
            anomaly = True
            solution = SOLUTION_MAP["health_keyword"]

        return {"anomaly_detected": anomaly, "recommended_solution": solution}


anomaly_service = AnomalyService()
