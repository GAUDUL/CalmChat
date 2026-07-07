import re

from .model_service import ModelService
from .rules import CRISIS_CONTEXT_SUPPRESS_RULES, CRISIS_KEYWORD_RULES, HEALTH_KEYWORD_RULES

# Terms that push confidence straight to "high" regardless of the LLM
# confirmation step, because they're unambiguous on their own.
_DIRECT_HIGH_CONFIDENCE_TERMS = (
    "죽고",
    "죽고싶",
    "자살",
    "자해",
    "suicide",
    "kill myself",
    "end my life",
    "chest pain",
    "short of breath",
    "hard to breathe",
    "119",
    "가슴 통증",
    "호흡 곤란",
    "숨쉬기 힘",
    "숨이 차",
)

# Model output is combined into a single 0-100 "vitality-compatible" scale so
# anomaly_service's existing thresholds/z-score baselines keep working without
# needing to be re-tuned for a totally different range.
_EMOTION_SCORE_MIDPOINT = 50
_EMOTION_SCORE_SPAN = 50


class EmotionEngine:
    NEGATION_WINDOW = 8

    def __init__(self, model_service: ModelService | None = None):
        self._model_service = model_service or ModelService()

    # ---- rule-based safety signals (independent of the emotion model) ----
    def _match_keywords(self, text: str, keyword_set) -> list[str]:
        return [kw for kw in keyword_set if kw in text]

    def _match_suppressors(self, text: str) -> list[str]:
        return [kw for kw in CRISIS_CONTEXT_SUPPRESS_RULES if kw in text]

    def _danger_confidence(self, text: str, matched_keywords: list[str], matched_suppressors: list[str]) -> str:
        if not matched_keywords:
            return "none"
        if matched_suppressors:
            return "suppressed"

        if any(term in keyword for keyword in matched_keywords for term in _DIRECT_HIGH_CONFIDENCE_TERMS):
            return "high"
        if re.search(r"(나|내가|myself|me).{0,12}(해치|hurt|죽|die)", text):
            return "high"
        return "ambiguous"

    def _safety_signal(self, text: str, matched_suppressors: list[str], signal_kind: str, keyword_set) -> tuple[bool, list[str], str]:
        matched = self._match_keywords(text, keyword_set)
        confidence = self._danger_confidence(text, matched, matched_suppressors) if matched else "none"
        return bool(matched), matched, confidence

    # ---- model-based emotion scoring ----

    def _to_emotion_score(self, positive_score: float, negative_score: float) -> float:
        net = positive_score - negative_score  # roughly -1..1
        score = _EMOTION_SCORE_MIDPOINT + net * _EMOTION_SCORE_SPAN
        return max(0.0, min(100.0, score))

    def extract(self, text: str) -> dict:
        model_result = self._model_service.predict(text)

        matched_suppressors = self._match_suppressors(text)

        crisis_flag, crisis_matched, crisis_confidence = self._safety_signal(
            text, matched_suppressors, "crisis", CRISIS_KEYWORD_RULES
        )
        health_flag, health_matched, health_confidence = self._safety_signal(
            text, matched_suppressors, "health", HEALTH_KEYWORD_RULES
        )

        # Fallback single confidence value, used by callers that don't care
        # which specific signal (crisis vs health) it came from.
        overall_confidence = "none"
        if crisis_flag or health_flag:
            overall_confidence = crisis_confidence if crisis_flag else health_confidence

        return {
            # 모델 기반 scoring
            "dominant": model_result["dominant"],  # e.g. "슬픔"
            "intensity": model_result["intensity"],  # e.g. 0.792
            "positive_score": model_result["positive_score"],
            "negative_score": model_result["negative_score"],
            "emotions": model_result["emotions"],
            "emotion_score": self._to_emotion_score(
                model_result["positive_score"], model_result["negative_score"]
            ),
            # rule 기반 위험 탐지
            "crisis_keyword_flag": crisis_flag,
            "health_keyword_flag": health_flag,
            "matched_keywords": {
                "crisis": crisis_matched,
                "health": health_matched,
            },
            "danger_confidence": overall_confidence,
            "danger_confidence_by_signal": {
                "crisis": crisis_confidence,
                "health": health_confidence,
            },
        }