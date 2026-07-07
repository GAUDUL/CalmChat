import re

from .rules import (
    CRISIS_CONTEXT_SUPPRESS_RULES,
    CRISIS_KEYWORD_RULES,
    EMOTION_RULES,
    ENERGY_RULES,
    HEALTH_CONTEXT_SUPPRESS_RULES,
    HEALTH_KEYWORD_RULES,
    NEGATION_TERMS,
    PHRASE_RULES,
)


class EmotionEngine:
    NEGATION_WINDOW = 8

    def _has_negation_before(self, text: str, start: int) -> bool:
        prefix = text[max(0, start - self.NEGATION_WINDOW):start].strip()
        return any(re.search(rf"(^|\s){re.escape(term)}($|\s)", prefix) for term in NEGATION_TERMS)

    def _has_negation_after(self, text: str, end: int) -> bool:
        suffix = text[end:end + self.NEGATION_WINDOW].strip()
        return any(pattern in suffix for pattern in ("지 않", "지않", "지는 않", "not"))

    def _match(
        self,
        text: str,
        rules: dict,
        *,
        suppress_negated_before: bool = False,
        suppress_negated_after: bool = False,
    ) -> tuple[float, list[str]]:
        score = 0.0
        matched_keywords = []
        occupied_spans = []
        for keyword, delta in sorted(rules.items(), key=lambda item: len(item[0]), reverse=True):
            start = text.find(keyword)
            if start == -1:
                continue

            end = start + len(keyword)
            if any(not (end <= span_start or start >= span_end) for span_start, span_end in occupied_spans):
                continue

            if suppress_negated_before and self._has_negation_before(text, start):
                continue

            if suppress_negated_after and self._has_negation_after(text, end):
                continue

            score += delta
            matched_keywords.append(keyword)
            occupied_spans.append((start, end))

        return score, matched_keywords

    def _matched_any(self, text: str, keywords: set[str]) -> list[tuple[str, int, int]]:
        matches = []
        for keyword in keywords:
            start = text.find(keyword)
            if start != -1:
                matches.append((keyword, start, start + len(keyword)))
        return matches

    def _nearby_suppressors(
        self,
        text: str,
        matches: list[tuple[str, int, int]],
        suppressor_matches: list[tuple[str, int, int]],
        window: int = 18,
    ) -> list[str]:
        nearby = []
        for _, start, end in matches:
            for suppressor, suppressor_start, suppressor_end in suppressor_matches:
                if suppressor_end < start - window or suppressor_start > end + window:
                    continue
                sentence_start = max(text.rfind(".", 0, start), text.rfind("?", 0, start), text.rfind("!", 0, start))
                sentence_end_candidates = [
                    idx for idx in (
                        text.find(".", end),
                        text.find("?", end),
                        text.find("!", end),
                    )
                    if idx != -1
                ]
                sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
                if not (sentence_start < suppressor_start < sentence_end):
                    continue
                nearby.append(suppressor)
        return nearby

    def _alert_context(self, text: str, keywords: set[str], suppress_rules: set[str]) -> tuple[bool, list[str], list[str]]:
        keyword_matches = self._matched_any(text, keywords)
        suppressor_matches = self._matched_any(text, suppress_rules)
        matched_keywords = [keyword for keyword, _, _ in keyword_matches]
        matched_suppressors = self._nearby_suppressors(text, keyword_matches, suppressor_matches)
        return bool(matched_keywords and not matched_suppressors), matched_keywords, matched_suppressors

    def _danger_confidence(self, text: str, matched_keywords: list[str], matched_suppressors: list[str]) -> str:
        if not matched_keywords:
            return "none"
        if matched_suppressors:
            return "suppressed"
        direct_terms = (
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
        if any(term in keyword for keyword in matched_keywords for term in direct_terms):
            return "high"
        if re.search(r"(나|내가|myself|me).{0,12}(해치|hurt|죽|die)", text):
            return "high"
        return "ambiguous"

    def extract(self, text: str) -> dict:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()

        emotion_delta = 0.0
        energy_delta = 0.0
        matched_keywords = {
            "phrase": [],
            "emotion_negative": [],
            "emotion_positive": [],
            "energy_negative": [],
            "energy_positive": [],
            "health": [],
            "crisis": [],
            "suppressed_health": [],
            "suppressed_crisis": [],
        }

        for phrase, delta in PHRASE_RULES:
            if phrase in normalized:
                emotion_delta += delta
                energy_delta += delta * 0.8
                matched_keywords["phrase"].append(phrase)

        score, matches = self._match(
            normalized,
            EMOTION_RULES["negative"],
            suppress_negated_after=True,
        )
        emotion_delta += score
        matched_keywords["emotion_negative"].extend(matches)

        score, matches = self._match(
            normalized,
            EMOTION_RULES["positive"],
            suppress_negated_before=True,
            suppress_negated_after=True,
        )
        emotion_delta += score
        matched_keywords["emotion_positive"].extend(matches)

        score, matches = self._match(
            normalized,
            ENERGY_RULES["negative"],
            suppress_negated_after=True,
        )
        energy_delta += score
        matched_keywords["energy_negative"].extend(matches)

        score, matches = self._match(
            normalized,
            ENERGY_RULES["positive"],
            suppress_negated_before=True,
            suppress_negated_after=True,
        )
        energy_delta += score
        matched_keywords["energy_positive"].extend(matches)

        health_keyword_flag, health_matches, health_suppressors = self._alert_context(
            normalized,
            HEALTH_KEYWORD_RULES,
            HEALTH_CONTEXT_SUPPRESS_RULES,
        )
        crisis_keyword_flag, crisis_matches, crisis_suppressors = self._alert_context(
            normalized,
            CRISIS_KEYWORD_RULES,
            CRISIS_CONTEXT_SUPPRESS_RULES,
        )
        matched_keywords["health"].extend(health_matches)
        matched_keywords["crisis"].extend(crisis_matches)
        matched_keywords["suppressed_health"].extend(health_suppressors)
        matched_keywords["suppressed_crisis"].extend(crisis_suppressors)
        crisis_confidence = self._danger_confidence(
            normalized,
            crisis_matches,
            crisis_suppressors,
        )
        health_confidence = self._danger_confidence(
            normalized,
            health_matches,
            health_suppressors,
        )
        danger_confidence = (
            "high"
            if "high" in {crisis_confidence, health_confidence}
            else "ambiguous"
            if "ambiguous" in {crisis_confidence, health_confidence}
            else "suppressed"
            if "suppressed" in {crisis_confidence, health_confidence}
            else "none"
        )

        if crisis_keyword_flag:
            # Keep crisis language out of generic keyword scoring, but still
            # reflect severe distress in the trend visible to caregivers.
            emotion_delta -= 8
            energy_delta -= 4

        return {
            "emotion_delta": emotion_delta,
            "energy_delta": energy_delta,
            "health_keyword_flag": health_keyword_flag,
            "crisis_keyword_flag": crisis_keyword_flag,
            "danger_confidence": danger_confidence,
            "danger_confidence_by_signal": {
                "crisis": crisis_confidence,
                "health": health_confidence,
            },
            "matched_keywords": matched_keywords,
        }
