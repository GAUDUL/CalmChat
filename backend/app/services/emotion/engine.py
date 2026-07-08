"""
app/services/emotion/engine.py

[교체 이력]
기존 사전 가중치(키워드 매칭) 방식의 감정 점수화를 KOTE(KcELECTRA)
+ Gemini 보조판단(죄책감/후회) + VAD(valence) 변환으로 교체.

크라이시스/헬스 키워드 탐지(안전 트리거 레이어)는 SafetyKeywordDetector로
로직 변경 없이 그대로 분리해 재사용한다 (safety_keywords.py).

processor.py의 호출 인터페이스(extract(text) -> dict)는 완전히 동일하게
유지하여 processor.py는 수정하지 않는다.

[energy 제거 - 2026-07]
energy는 별도로 점수화하지 않기로 확정되어 energy_delta / CRISIS_ENERGY_PENALTY
를 전부 제거함. 이제 emotion만 점수화한다.

[유지해야 하는 대칭 관계 - 중요]
원본 engine.py는 crisis_keyword_flag가 True일 때 emotion_delta -= 8을
적용했고, processor.py는 외부에서 crisis_keyword_flag_override가 False로
확인된 경우 이 -8을 정확히 상쇄하는 +8을 더한다
(`if delta["crisis_keyword_flag"] and crisis_keyword_flag_override is False: ...`).
이 대칭이 깨지면 override 로직이 오작동하므로, 아래에서도 동일하게 -8을 적용한다.
"""

import re
import logging

from .kote_classifier import kote_classifier
from .vad_scoring import compute_emotion_delta
from .safety_keywords import safety_keyword_detector

logger = logging.getLogger(__name__)

# 원본 engine.py와 동일한 crisis 페널티 (processor.py의 override 상쇄 로직과 대칭 유지)
CRISIS_EMOTION_PENALTY = -8


class EmotionEngine:
    def extract(self, text: str) -> dict:
        # 원본 engine.py와 동일한 정규화 (안전 레이어 키워드 매칭에 사용)
        # TODO: but 사용자의 text는 한국어 or 영어로 들어올 것이라 예상 (무엇보다 테스트는 한국어 위주임)
        # 그래서 normalized를 하려면 한국어 버전 정규화도 필요
        normalized = re.sub(r"\s+", " ", text.lower()).strip()

        # 1. 안전 트리거 레이어 (기존 rules.py 기반 로직 그대로, 변경 없음)
        safety_result = safety_keyword_detector.detect(normalized)

        # 2. KOTE 기반 감정 분류 (44라벨 -> 8클러스터 max-pooling)
        #    + 자기지향_부정(죄책감/후회) 후보인 경우 Gemini 보조판단 자동 트리거
        #    (원문 text 사용 - KOTE 토크나이저는 소문자/공백정규화에 의존하지 않음)
        # "label_probs": label_probs,
        # "cluster_probs": cluster_probs,
        # "guilt_regret_llm_checked": guilt_checked,
        # "guilt_regret_llm_result": guilt_result,
        kote_result = kote_classifier.analyze(text)

        # 3. VAD(valence) 변환 (점수화) - 클러스터 확률 -> emotion_delta
        emotion_delta = compute_emotion_delta(kote_result["cluster_probs"])

        # 4. crisis 페널티 적용 (원본과 동일한 -8, processor.py 상쇄 로직과 대칭 유지)
        if safety_result["crisis_keyword_flag"]:
            emotion_delta += CRISIS_EMOTION_PENALTY

        return {
            "emotion_delta": emotion_delta,
            "health_keyword_flag": safety_result["health_keyword_flag"],
            "crisis_keyword_flag": safety_result["crisis_keyword_flag"],
            "danger_confidence": safety_result["danger_confidence"],
            "danger_confidence_by_signal": safety_result["danger_confidence_by_signal"],
            "matched_keywords": safety_result["matched_keywords"],
            # 아래는 processor.py의 기존 로깅에서는 쓰이지 않지만,
            # 추후 디버깅/캘리브레이션용으로 필요하면 활용 가능하도록 포함해둠.
            "cluster_probs": kote_result["cluster_probs"],
            "guilt_regret_llm_checked": kote_result["guilt_regret_llm_checked"],
            "guilt_regret_llm_result": kote_result["guilt_regret_llm_result"],
        }