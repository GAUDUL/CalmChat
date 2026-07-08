"""
app/services/emotion/safety_keywords.py

[분리 이력]
기존 engine.py에서 크라이시스/헬스 키워드 탐지 로직만 그대로 분리.
로직/알고리즘 변경 없음 (안전 트리거 레이어이므로 감정 스코어링 교체와 무관하게 유지).

원본 engine.py에서 이 파일로 옮긴 부분: _matched_any, _nearby_suppressors,
_alert_context, _danger_confidence. 문장 단위 컨텍스트 억제 방식
(CRISIS_CONTEXT_SUPPRESS_RULES / HEALTH_CONTEXT_SUPPRESS_RULES)을 그대로 사용한다.

[제외한 부분]
_has_negation_before/_has_negation_after, _match()는 EMOTION_RULES/ENERGY_RULES
가중치 점수화(_match)에서만 쓰이던 로직으로, 이는 KOTE 기반 분류로 대체되어
더 이상 필요하지 않으므로 이 파일에는 포함하지 않음.
"""

import re

from .rules import (
    CRISIS_CONTEXT_SUPPRESS_RULES,
    CRISIS_KEYWORD_RULES,
    HEALTH_CONTEXT_SUPPRESS_RULES,
    HEALTH_KEYWORD_RULES,
)


class SafetyKeywordDetector:
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

    def detect(self, text: str) -> dict:
        """
        원본 engine.py의 extract()에서 크라이시스/헬스 관련 부분만 그대로 재현.
        text는 이미 정규화(lower + 공백 정리)된 상태로 전달되어야 한다.
        """
        health_keyword_flag, health_matches, health_suppressors = self._alert_context(
            text, HEALTH_KEYWORD_RULES, HEALTH_CONTEXT_SUPPRESS_RULES,
        )
        crisis_keyword_flag, crisis_matches, crisis_suppressors = self._alert_context(
            text, CRISIS_KEYWORD_RULES, CRISIS_CONTEXT_SUPPRESS_RULES,
        )

        crisis_confidence = self._danger_confidence(text, crisis_matches, crisis_suppressors)
        health_confidence = self._danger_confidence(text, health_matches, health_suppressors)
        danger_confidence = (
            "high"
            if "high" in {crisis_confidence, health_confidence}
            else "ambiguous"
            if "ambiguous" in {crisis_confidence, health_confidence}
            else "suppressed"
            if "suppressed" in {crisis_confidence, health_confidence}
            else "none"
        )

        return {
            "health_keyword_flag": health_keyword_flag,
            "crisis_keyword_flag": crisis_keyword_flag,
            "danger_confidence": danger_confidence,
            "danger_confidence_by_signal": {
                "crisis": crisis_confidence,
                "health": health_confidence,
            },
            "matched_keywords": {
                "health": health_matches,
                "crisis": crisis_matches,
                "suppressed_health": health_suppressors,
                "suppressed_crisis": crisis_suppressors,
            },
        }


safety_keyword_detector = SafetyKeywordDetector()