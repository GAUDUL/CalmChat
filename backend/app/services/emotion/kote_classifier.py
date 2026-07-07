"""
app/services/emotion/kote_classifier.py

Pretrained KOTE(searle-j/kote_for_easygoing_people) 기반 감정 추출 모듈.

[배경 요약 - lift 분석 결과]
- 44개 fine label 대부분(긍정/슬픔/불안/분노 계열)은 base-rate 대비 lift가 이론적
  상한의 60~90% 수준으로 신뢰 가능함을 확인 (재학습 없이 pretrained 그대로 사용, B안 확정).
- 단, '자기지향_부정' 클러스터 내부에서도 한심함/열등감/부끄러움은 lift > 2로 양호했으나
  '죄책감'(및 KOTE에 대응 라벨이 없는 '후회')은 lift < 1, 즉 base-rate보다도 못 맞춰
  신뢰 불가로 판정됨. 이 부분만 Gemini 보조판단으로 보정한다 (llm_service 경유).

파인튜닝 없이 pretrained 모델을 그대로 사용한다 (45라벨 확장은 표본 부족으로 보류, B안).
"""

import logging
from typing import Dict, List

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

MODEL_NAME = "searle-j/kote_for_easygoing_people"
MAX_LEN = 128

KOTE_LABELS_REFERENCE = [
    "불평/불만", "환영/호의", "감동/감탄", "지긋지긋", "고마움",
    "슬픔", "화남/분노", "존경", "기대감", "우쭐댐/무시함",
    "안타까움/실망", "비장함", "의심/불신", "뿌듯함", "편안/쾌적",
    "신기함/관심", "아껴주는", "부끄러움", "공포/무서움", "절망",
    "한심함", "역겨움/징그러움", "짜증", "어이없음", "없음",
    "패배/자기혐오", "귀찮음", "힘듦/지침", "즐거움/신남", "깨달음",
    "죄책감", "증오/혐오", "흐뭇함(귀여움/예쁨)", "당황/난처", "경악",
    "부담/안_내킴", "서러움", "재미없음", "불쌍함/연민", "놀람",
    "행복", "불안/걱정", "기쁨", "안심/신뢰",
]

# 매크로 클러스터 정의 (검증 완료본 - '불평/불만' 누락 버그 수정된 최종 버전)
MACRO_CLUSTERS = {
    "긍정_기쁨": ["기쁨", "행복", "즐거움/신남", "뿌듯함", "흐뭇함(귀여움/예쁨)", "감동/감탄"],
    "긍정_안정": ["편안/쾌적", "안심/신뢰", "아껴주는", "환영/호의", "고마움", "존경"],
    "슬픔_상실": ["슬픔", "안타까움/실망", "절망", "서러움", "불쌍함/연민"],
    "자기지향_부정": ["부끄러움", "죄책감", "패배/자기혐오", "한심함"],
    "불안_긴장": ["불안/걱정", "공포/무서움", "부담/안_내킴", "힘듦/지침"],
    "분노_짜증": ["불평/불만", "화남/분노", "짜증", "지긋지긋", "귀찮음", "증오/혐오", "역겨움/징그러움", "어이없음"],
    "당황_혼란": ["당황/난처", "의심/불신", "경악", "놀람", "신기함/관심"],
    "기타_중립": ["없음", "깨달음", "비장함", "우쭐댐/무시함", "재미없음", "기대감"],
}

_all_clustered = [lbl for members in MACRO_CLUSTERS.values() for lbl in members]
assert len(_all_clustered) == 44, f"클러스터 매핑 라벨 수가 44가 아님: {len(_all_clustered)}"
assert set(_all_clustered) == set(KOTE_LABELS_REFERENCE), "클러스터 매핑에 누락/중복된 라벨이 있음"
assert len(set(_all_clustered)) == 44, "클러스터 매핑에 중복된 라벨이 있음"

# lift 분석에서 신뢰 불가로 판정된 라벨/클러스터 (Gemini 보조판단 트리거 대상)
GUILT_REGRET_LABEL = "죄책감"
GUILT_REGRET_CLUSTER = "자기지향_부정"

# Gemini 확인 후 클러스터 확률 보정값 (초안 - 팀 리뷰 필요)
GUILT_CONFIRMED_FLOOR = 0.6   # Gemini가 "맞다"고 확인 -> 최소 이 값 이상으로 보정
GUILT_REJECTED_CEILING = 0.05  # Gemini가 "아니다"라고 확인 -> 이 값 이하로 억제 (KOTE 오탐 처리)


class KoteClassifier:
    """싱글턴. llm_service와 동일한 패턴(모듈 하단에서 인스턴스 생성)."""

    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = None
        self.label_list: List[str] = []
        self._loaded = False

    def _lazy_load(self):
        if self._loaded:
            return
        logger.info("Loading KOTE model: %s", MODEL_NAME)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME, problem_type="multi_label_classification"
        )
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        self.model.to(self.device)
        self.model.eval()
        self.label_list = self._verify_checkpoint_label_order()
        self._loaded = True
        logger.info("KOTE model loaded on device=%s", self.device)

    def _verify_checkpoint_label_order(self) -> List[str]:
        """체크포인트 라벨 순서를 진실의 원천으로 fail-fast 검증 (조용히 넘어가지 않음)."""
        id2label = {int(k): v for k, v in self.model.config.id2label.items()}
        assert len(id2label) == 44, f"라벨 개수가 44가 아닙니다: {len(id2label)}"
        ordered = [id2label[i] for i in range(44)]
        mismatch = [i for i in range(44) if ordered[i] != KOTE_LABELS_REFERENCE[i]]
        if mismatch:
            raise ValueError(
                f"체크포인트 라벨 순서가 참고 리스트와 인덱스 {mismatch}에서 다릅니다. "
                "조용히 진행하지 말고 반드시 확인 후 재실행하세요."
            )
        return ordered

    def _raw_label_probs(self, text: str) -> np.ndarray:
        self._lazy_load()
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LEN)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
        return torch.sigmoid(logits).squeeze().cpu().numpy()

    def _cluster_probs(self, label_probs_arr: np.ndarray) -> Dict[str, float]:
        """클러스터 내 라벨들의 max-pooling (약한 개별 라벨도 클러스터 단위에선 신호가 살아남)."""
        result = {}
        for cluster, members in MACRO_CLUSTERS.items():
            idxs = [self.label_list.index(lbl) for lbl in members]
            result[cluster] = float(label_probs_arr[idxs].max())
        return result

    def analyze(self, text: str) -> dict:
        """
        반환:
          label_probs: {라벨: 확률} 44개 전체 (로깅/디버깅용)
          cluster_probs: {클러스터: 확률} 8개 (VAD 변환 입력)
          guilt_regret_llm_checked: Gemini 보조판단 호출 여부
          guilt_regret_llm_result: True/False/None (None=LLM 호출 실패, 보수적으로 원 확률 유지)
        """
        label_probs_arr = self._raw_label_probs(text)
        label_probs = {lbl: float(label_probs_arr[i]) for i, lbl in enumerate(self.label_list)}
        cluster_probs = self._cluster_probs(label_probs_arr)

        guilt_checked = False
        guilt_result = None

        top2_clusters = sorted(cluster_probs, key=cluster_probs.get, reverse=True)[:2]
        if GUILT_REGRET_CLUSTER in top2_clusters:
            # 자기지향_부정이 후보로 뜬 경우에만 Gemini 호출 (매 메시지 호출 방지, 비용/지연 통제)
            guilt_checked = True
            guilt_result = llm_service.confirm_guilt_or_regret_signal(text)

            if guilt_result is True:
                cluster_probs[GUILT_REGRET_CLUSTER] = max(
                    cluster_probs[GUILT_REGRET_CLUSTER], GUILT_CONFIRMED_FLOOR
                )
            elif guilt_result is False:
                cluster_probs[GUILT_REGRET_CLUSTER] = min(
                    cluster_probs[GUILT_REGRET_CLUSTER], GUILT_REJECTED_CEILING
                )
            # guilt_result is None -> KOTE 원 확률 그대로 유지 (LLM 실패 시 보수적 fallback)

        logger.info(
            "kote_analysis raw_guilt_prob=%.4f guilt_checked=%s guilt_llm_result=%s cluster_probs=%s",
            label_probs.get(GUILT_REGRET_LABEL, -1.0),
            guilt_checked,
            guilt_result,
            {k: round(v, 3) for k, v in cluster_probs.items()},
        )

        return {
            "label_probs": label_probs,
            "cluster_probs": cluster_probs,
            "guilt_regret_llm_checked": guilt_checked,
            "guilt_regret_llm_result": guilt_result,
        }


kote_classifier = KoteClassifier()