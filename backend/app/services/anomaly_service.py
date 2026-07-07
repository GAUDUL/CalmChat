from dataclasses import dataclass
import json
import logging

import numpy as np
from sqlalchemy.orm import Session

from app.models.db_models import MetricRecord


LOW_SCORE_THRESHOLD = 35
CAUTION_Z_SCORE_THRESHOLD = -1.0
WARNING_Z_SCORE_THRESHOLD = -1.5
DROP_FROM_BASELINE_CAUTION = 4
DROP_FROM_BASELINE_WARNING = 5
EMA_ALPHA = 0.35
MIN_STATISTICAL_RECORDS = 5
STD_FLOOR = 4
TREND_DROP_THRESHOLD = 3
HYSTERESIS_STABLE_RECORDS = 3
MAD_SCALE = 1.4826
CONTACT_GAP_DAYS = 3

logger = logging.getLogger(__name__)

RISK_ORDER = {
    "normal": 0,
    "caution": 1,
    "warning": 2,
    "danger": 3,
}

SOLUTION_MAP = {
    "normal": {
        "message": None,
        "actions": [],
    },
    "caution": {
        "message": "Minor emotional changes have been detected. Light activity and reminiscence conversations are recommended.",
        "actions": [
            "Suggest a light walk or spending some time in the sunlight.",
            "Encourage conversations about recent happy memories or meaningful experiences.",
        ],
    },
    "warning": {
        "message": "A noticeable decline in emotional well-being or energy has been detected. Active check-ins are recommended.",
        "actions": [
            "Play a short check-in message using a family member's cloned voice.",
            "Recommend favorite music or calming activities that the user enjoys.",
            "Encourage the caregiver to check on the user's condition.",
        ],
    },
    "danger": {
        "message": "High-risk health or safety signals have been detected. Immediate intervention is recommended.",
        "actions": [
            "Send an automatic alert to the caregiver.",
            "Display an emergency call button.",
            "If chest pain, breathing difficulties, or self-harm expressions are present, advise contacting emergency services immediately.",
        ],
    },
}


@dataclass
class MetricSignal:
    name: str
    risk_level: str
    reason: str
    latest_score: float | None = None
    baseline_score: float | None = None
    std_score: float | None = None
    mad_score: float | None = None
    z_score: float | None = None
    change_rate: float | None = None
    drop_from_baseline: float | None = None
    required_drop: float | None = None
    trend_declining: bool = False
    record_count: int = 0
    matched_keywords: list[str] | None = None


class AnomalyService:
    def _ema_latest_first(self, scores: np.ndarray) -> np.ndarray:
        if len(scores) == 0:
            return scores

        chronological = scores[::-1]
        smoothed = [float(chronological[0])]
        for score in chronological[1:]:
            smoothed.append((EMA_ALPHA * float(score)) + ((1 - EMA_ALPHA) * smoothed[-1]))

        return np.array(smoothed[::-1])

    def _is_declining_trend(self, scores: np.ndarray) -> bool:
        if len(scores) < 3:
            return False

        latest, previous, before_previous = scores[:3]
        return bool(latest < previous < before_previous)

    def _welford_std(self, scores: np.ndarray) -> float:
        if len(scores) < 2:
            return 0.0

        mean = 0.0
        m2 = 0.0
        count = 0
        for score in scores:
            count += 1
            delta = float(score) - mean
            mean += delta / count
            m2 += delta * (float(score) - mean)

        return float(np.sqrt(m2 / (count - 1))) if count > 1 else 0.0

    def _mad_std(self, scores: np.ndarray) -> float:
        if len(scores) == 0:
            return 0.0

        median = float(np.median(scores))
        mad = float(np.median(np.abs(scores - median)))
        return mad * MAD_SCALE

    def _baseline_stats(self, scores: np.ndarray) -> dict:
        welford_std = self._welford_std(scores)
        mad_std = self._mad_std(scores)
        if mad_std <= 1e-6:
            robust_std = STD_FLOOR
        else:
            robust_std = max(min(welford_std, mad_std), STD_FLOOR)
        return {
            "baseline": float(np.median(scores)),
            "std": robust_std,
            "mad_std": mad_std,
        }

    def _analyze_scores(self, name: str, scores: np.ndarray) -> MetricSignal | None:
        if len(scores) == 0:
            return None

        smoothed = self._ema_latest_first(scores)
        raw_latest = float(scores[0])
        trend_declining = self._is_declining_trend(smoothed)

        if raw_latest < LOW_SCORE_THRESHOLD:
            signal = self._absolute_threshold_signal(name, raw_latest, len(scores))
            signal.trend_declining = trend_declining
            return signal

        if len(scores) < MIN_STATISTICAL_RECORDS:
            return None

        baseline_scores = smoothed[1:]
        stats = self._baseline_stats(baseline_scores)
        baseline = stats["baseline"]
        std = stats["std"]
        mad_std = stats["mad_std"]
        z_score = (raw_latest - baseline) / std
        change_rate = ((raw_latest - baseline) / max(abs(baseline), 1e-6)) * 100
        drop_from_baseline = baseline - raw_latest
        caution_drop = max(DROP_FROM_BASELINE_CAUTION, std * abs(CAUTION_Z_SCORE_THRESHOLD))
        warning_drop = max(DROP_FROM_BASELINE_WARNING, std * abs(WARNING_Z_SCORE_THRESHOLD))

        if (
            drop_from_baseline >= warning_drop
            and z_score <= WARNING_Z_SCORE_THRESHOLD
        ):
            return MetricSignal(
                name=name,
                risk_level="warning",
                reason=f"{name} score dropped sharply against the 14-day baseline.",
                latest_score=raw_latest,
                baseline_score=baseline,
                std_score=std,
                mad_score=mad_std,
                z_score=z_score,
                change_rate=change_rate,
                drop_from_baseline=drop_from_baseline,
                required_drop=warning_drop,
                trend_declining=trend_declining,
                record_count=len(scores),
            )

        if (
            (
                drop_from_baseline >= caution_drop
                and z_score <= CAUTION_Z_SCORE_THRESHOLD
            )
            or (
                trend_declining
                and drop_from_baseline >= TREND_DROP_THRESHOLD
            )
        ):
            return MetricSignal(
                name=name,
                risk_level="caution",
                reason=f"{name} score shows a concerning downward pattern.",
                latest_score=raw_latest,
                baseline_score=baseline,
                std_score=std,
                mad_score=mad_std,
                z_score=z_score,
                change_rate=change_rate,
                drop_from_baseline=drop_from_baseline,
                required_drop=caution_drop,
                trend_declining=trend_declining,
                record_count=len(scores),
            )

        return None

    def _absolute_threshold_signal(self, name: str, latest_score: float, record_count: int) -> MetricSignal:
        return MetricSignal(
            name=name,
            risk_level="warning",
            reason=f"{name} score is below the absolute safety threshold.",
            latest_score=float(latest_score),
            record_count=record_count,
            required_drop=LOW_SCORE_THRESHOLD,
        )

    def _recent_stable_count(self, records: list[MetricRecord]) -> int:
        stable_count = 0
        for record in records:
            if record.health_keyword_flag or record.crisis_keyword_flag:
                break
            emotion = record.emotion_score
            energy = record.energy_score
            if emotion is None or energy is None:
                break
            if emotion >= LOW_SCORE_THRESHOLD and energy >= LOW_SCORE_THRESHOLD:
                stable_count += 1
                continue
            break
        return stable_count

    def _apply_hysteresis(
        self,
        risk_level: str,
        signals: list[MetricSignal],
        records: list[MetricRecord],
        decision_log: list[dict],
    ) -> tuple[str, list[MetricSignal]]:
        if len(records) < MIN_STATISTICAL_RECORDS + HYSTERESIS_STABLE_RECORDS:
            return risk_level, signals

        stable_count = self._recent_stable_count(records[:HYSTERESIS_STABLE_RECORDS])
        historical_records = records[HYSTERESIS_STABLE_RECORDS:]
        if not historical_records:
            return risk_level, signals

        historical_signals = self._statistical_signals(historical_records)
        if not historical_signals:
            return risk_level, signals

        held_risk = max(historical_signals, key=lambda signal: RISK_ORDER[signal.risk_level]).risk_level
        if RISK_ORDER[held_risk] <= RISK_ORDER[risk_level]:
            return risk_level, signals

        if stable_count >= HYSTERESIS_STABLE_RECORDS:
            decision_log.append({
                "stage": "hysteresis",
                "decision": "downgrade_released",
                "from": held_risk,
                "to": risk_level,
                "stable_count": stable_count,
            })
            return risk_level, signals

        held_signal = MetricSignal(
            name="hysteresis",
            risk_level=held_risk,
            reason="Previous elevated risk is held until stable readings continue.",
            record_count=len(records),
        )
        decision_log.append({
            "stage": "hysteresis",
            "decision": "held_previous_risk",
            "held_risk": held_risk,
            "current_risk": risk_level,
            "stable_count": stable_count,
        })
        return held_risk, [held_signal]

    def _statistical_signals(self, records: list[MetricRecord]) -> list[MetricSignal]:
        emotion_scores = np.array([r.emotion_score for r in records if r.emotion_score is not None])
        energy_scores = np.array([r.energy_score for r in records if r.energy_score is not None])

        signals = []
        emotion_signal = self._analyze_scores("emotion", emotion_scores)
        if emotion_signal:
            signals.append(emotion_signal)

        energy_signal = self._analyze_scores("energy", energy_scores)
        if energy_signal:
            signals.append(energy_signal)

        return signals

    def _result(
        self,
        risk_level: str,
        anomaly_types: list[str] | None = None,
        signals: list[MetricSignal] | None = None,
        decision_log: list[dict] | None = None,
    ) -> dict:
        solution = SOLUTION_MAP[risk_level]
        result = {
            "anomaly_detected": risk_level != "normal",
            "risk_level": risk_level,
            "anomaly_types": anomaly_types or [],
            "recommended_solution": solution["message"],
            "feedback_actions": solution["actions"],
            "signals": [signal.__dict__ for signal in signals or []],
            "decision_log": decision_log or [],
        }
        logger.info("anomaly_decision=%s", json.dumps(result, ensure_ascii=False, default=str))
        return result

    def detect(self, db: Session, user_id: int, window: int = 14) -> dict:
        records = (
            db.query(MetricRecord)
            .filter(MetricRecord.user_id == user_id)
            .order_by(MetricRecord.recorded_at.desc())
            .limit(window)
            .all()
        )
        decision_log = [{
            "stage": "input",
            "user_id": user_id,
            "record_count": len(records),
            "window": window,
        }]
        if not records:
            decision_log.append({"stage": "priority", "decision": "normal", "reason": "no_records"})
            return self._result("normal", decision_log=decision_log)

        latest = records[0]
        if latest.recorded_at and latest.recorded_at.hour < 6:
            decision_log.append({
                "stage": "temporal_context",
                "signal": "late_night_or_early_morning",
                "recorded_hour": latest.recorded_at.hour,
                "used_as": "auxiliary_only",
            })
        if len(records) > 1 and latest.recorded_at and records[1].recorded_at:
            contact_gap_days = (latest.recorded_at - records[1].recorded_at).total_seconds() / 86400
            if contact_gap_days >= CONTACT_GAP_DAYS:
                decision_log.append({
                    "stage": "temporal_context",
                    "signal": "contact_gap",
                    "gap_days": round(contact_gap_days, 2),
                    "used_as": "auxiliary_only",
                })

        # Priority 1: clinical danger signals are decided before statistical checks.
        if latest.crisis_keyword_flag:
            return self._result(
                "danger",
                anomaly_types=["crisis_keyword"],
                signals=[
                    MetricSignal(
                        name="safety",
                        risk_level="danger",
                        reason="Self-harm or crisis language was detected.",
                    ),
                ],
                decision_log=decision_log + [{
                    "stage": "priority",
                    "decision": "danger",
                    "reason": "crisis_keyword_flag",
                }],
            )

        if latest.health_keyword_flag:
            return self._result(
                "danger",
                anomaly_types=["health_keyword"],
                signals=[
                    MetricSignal(
                        name="health",
                        risk_level="danger",
                        reason="Health or emergency keyword was detected.",
                    ),
                ],
                decision_log=decision_log + [{
                    "stage": "priority",
                    "decision": "danger",
                    "reason": "health_keyword_flag",
                }],
            )

        if len(records) < MIN_STATISTICAL_RECORDS:
            absolute_signals = []
            if latest.emotion_score is not None and latest.emotion_score < LOW_SCORE_THRESHOLD:
                absolute_signals.append(
                    self._absolute_threshold_signal("emotion", latest.emotion_score, len(records))
                )
            if latest.energy_score is not None and latest.energy_score < LOW_SCORE_THRESHOLD:
                absolute_signals.append(
                    self._absolute_threshold_signal("energy", latest.energy_score, len(records))
                )

            if absolute_signals:
                decision_log.append({
                    "stage": "cold_start",
                    "decision": "warning",
                    "reason": "absolute_safety_threshold",
                })
                return self._result(
                    "warning",
                    anomaly_types=[f"low_{signal.name}" for signal in absolute_signals],
                    signals=absolute_signals,
                    decision_log=decision_log,
                )

            decision_log.append({
                "stage": "cold_start",
                "decision": "statistics_skipped",
                "reason": f"record_count_below_{MIN_STATISTICAL_RECORDS}",
            })
            return self._result("normal", decision_log=decision_log)

        signals = self._statistical_signals(records)
        if not signals:
            risk_level, signals = self._apply_hysteresis("normal", [], records, decision_log)
            anomaly_types = ["hysteresis"] if risk_level != "normal" else []
            decision_log.append({
                "stage": "priority",
                "decision": risk_level,
                "reason": "no_current_statistical_signal",
            })
            return self._result(
                risk_level,
                anomaly_types=anomaly_types,
                signals=signals,
                decision_log=decision_log,
            )

        # Priority 2 and 3: choose the single most severe score signal.
        risk_level = max(signals, key=lambda signal: RISK_ORDER[signal.risk_level]).risk_level
        risk_level, signals = self._apply_hysteresis(risk_level, signals, records, decision_log)
        anomaly_types = [f"low_{signal.name}" for signal in signals if signal.name in {"emotion", "energy"}]
        decision_log.append({
            "stage": "priority",
            "decision": risk_level,
            "reason": "statistical_signal",
            "selected_signal": max(signals, key=lambda signal: RISK_ORDER[signal.risk_level]).__dict__,
        })
        return self._result(
            risk_level,
            anomaly_types=anomaly_types,
            signals=signals,
            decision_log=decision_log,
        )


anomaly_service = AnomalyService()
