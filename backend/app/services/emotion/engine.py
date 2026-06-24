from .rules import EMOTION_RULES, ENERGY_RULES, PHRASE_RULES


class EmotionEngine:

    def __init__(self):
        pass

    def _match(self, text: str, rules: dict) -> float:
        score = 0.0

        for keyword, delta in rules.items():
            if keyword in text:
                score += delta

        return score

    def extract(self, text: str) -> dict:
        text = text.lower()

        emotion_delta = 0.0
        energy_delta = 0.0

        # phrase 먼저 (중요)
        for phrase, delta in PHRASE_RULES:
            if phrase in text:
                emotion_delta += delta
                energy_delta += delta * 0.8  # 약하게 영향

        # emotion
        emotion_delta += self._match(text, EMOTION_RULES["negative"])
        emotion_delta += self._match(text, EMOTION_RULES["positive"])

        # energy
        energy_delta += self._match(text, ENERGY_RULES["negative"])
        energy_delta += self._match(text, ENERGY_RULES["positive"])

        return {
            "emotion_delta": emotion_delta,
            "energy_delta": energy_delta,
        }