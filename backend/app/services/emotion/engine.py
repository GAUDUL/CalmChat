import re

from .rules import (
    EMOTION_RULES,
    ENERGY_RULES,
    HEALTH_CONTEXT_SUPPRESS_RULES,
    HEALTH_KEYWORD_RULES,
    PHRASE_RULES,
)


class EmotionEngine:
    def _match(self, text: str, rules: dict) -> float:
        score = 0.0

        for keyword, delta in rules.items():
            if keyword in text:
                score += delta

        return score

    def _has_any(self, text: str, keywords: set[str]) -> bool:
        # 후보 키워드 포함 여부 확인.
        return any(keyword in text for keyword in keywords)

    def _has_health_alert_context(self, text: str) -> bool:
        has_health_keyword = self._has_any(text, HEALTH_KEYWORD_RULES)
        has_suppress_context = self._has_any(text, HEALTH_CONTEXT_SUPPRESS_RULES)

        # 건강 후보 표현은 있되, 부정/회상/타인 이야기 맥락은 제외.
        return has_health_keyword and not has_suppress_context

    def extract(self, text: str) -> dict:
        # Whisper 출력 정규화.
        text = re.sub(r"\s+", " ", text.lower()).strip()

        emotion_delta = 0.0
        energy_delta = 0.0

        # 문장 단위 표현 우선 반영.
        for phrase, delta in PHRASE_RULES:
            if phrase in text:
                emotion_delta += delta
                energy_delta += delta * 0.8  # 감정 변화의 컨디션 영향 반영.

        # 감정 점수 반영.
        emotion_delta += self._match(text, EMOTION_RULES["negative"])
        emotion_delta += self._match(text, EMOTION_RULES["positive"])

        # 에너지 점수 반영.
        energy_delta += self._match(text, ENERGY_RULES["negative"])
        energy_delta += self._match(text, ENERGY_RULES["positive"])

        return {
            "emotion_delta": emotion_delta,
            "energy_delta": energy_delta,
            "health_keyword_flag": self._has_health_alert_context(text),
        }
