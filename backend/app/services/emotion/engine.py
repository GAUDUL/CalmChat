import re

from .rules import (
    CRISIS_CONTEXT_SUPPRESS_RULES,
    CRISIS_KEYWORD_RULES,
    EMOTION_RULES,
    ENERGY_RULES,
    HEALTH_CONTEXT_SUPPRESS_RULES,
    HEALTH_KEYWORD_RULES,
    PHRASE_RULES,
)


class EmotionEngine:
    def _match(self, text: str, rules: dict) -> float:
        return sum(delta for keyword, delta in rules.items() if keyword in text)

    def _has_any(self, text: str, keywords: set[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _has_health_alert_context(self, text: str) -> bool:
        return self._has_any(text, HEALTH_KEYWORD_RULES) and not self._has_any(
            text,
            HEALTH_CONTEXT_SUPPRESS_RULES,
        )

    def _has_crisis_context(self, text: str) -> bool:
        return self._has_any(text, CRISIS_KEYWORD_RULES) and not self._has_any(
            text,
            CRISIS_CONTEXT_SUPPRESS_RULES,
        )

    def extract(self, text: str) -> dict:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()

        emotion_delta = 0.0
        energy_delta = 0.0

        for phrase, delta in PHRASE_RULES:
            if phrase in normalized:
                emotion_delta += delta
                energy_delta += delta * 0.8

        emotion_delta += self._match(normalized, EMOTION_RULES["negative"])
        emotion_delta += self._match(normalized, EMOTION_RULES["positive"])

        energy_delta += self._match(normalized, ENERGY_RULES["negative"])
        energy_delta += self._match(normalized, ENERGY_RULES["positive"])

        crisis_keyword_flag = self._has_crisis_context(normalized)
        if crisis_keyword_flag:
            # Keep crisis language out of generic keyword scoring, but still
            # reflect severe distress in the trend visible to caregivers.
            emotion_delta -= 8
            energy_delta -= 4

        return {
            "emotion_delta": emotion_delta,
            "energy_delta": energy_delta,
            "health_keyword_flag": self._has_health_alert_context(normalized),
            "crisis_keyword_flag": crisis_keyword_flag,
        }
