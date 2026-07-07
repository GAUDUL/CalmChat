"""
app/services/emotion/vad_scoring.py

8개 매크로 클러스터 확률 -> emotion_delta / energy_delta 변환 (점수화 단계).

[중요 - 팀 리뷰 필요]
아래 CLUSTER_VAD 좌표는 Russell의 circumplex model(감정을 Valence-Arousal 평면에
배치하는 표준 모델)을 참고한 1차 초안값이다. 게이미피케이션/스코어링 담당(임수현)과
스케일 및 의미(emotion_score/energy_score가 UI에서 어떻게 쓰이는지)를 맞춘 뒤
최종 확정할 것. 지금 값 그대로 프로덕션에 반영하지 말 것.

state_service.py의 EmotionStateService.update()가 emotion_delta/energy_delta를
받아 기존 점수에 누적(decay 포함)하는 구조이므로, 이 델타값은 "이번 대화 turn
하나가 전체 점수에 미치는 변화폭"으로 해석된다. processor.py의 기존 crisis
보정치(+8)와 스케일을 맞추기 위해 MAX_DELTA를 8.0으로 설정함.
"""

from typing import Dict, Tuple

from .kote_classifier import MACRO_CLUSTERS

# Valence: -1(부정) ~ +1(긍정), Arousal: 0(낮음/차분함) ~ 1(높음/각성)
# Dominance는 현재 미사용 (추후 발화 주도성/무력감 관련 지표에 활용 검토 - 미착수)
CLUSTER_VAD = {
    "긍정_기쁨":     {"valence": 0.9,  "arousal": 0.7, "dominance": 0.6},
    "긍정_안정":     {"valence": 0.7,  "arousal": 0.2, "dominance": 0.6},
    "슬픔_상실":     {"valence": -0.7, "arousal": 0.3, "dominance": 0.2},
    "자기지향_부정": {"valence": -0.6, "arousal": 0.3, "dominance": 0.1},
    "불안_긴장":     {"valence": -0.5, "arousal": 0.8, "dominance": 0.2},
    "분노_짜증":     {"valence": -0.6, "arousal": 0.8, "dominance": 0.6},
    "당황_혼란":     {"valence": -0.2, "arousal": 0.6, "dominance": 0.3},
    "기타_중립":     {"valence": 0.0,  "arousal": 0.3, "dominance": 0.5},
}

assert set(CLUSTER_VAD.keys()) == set(MACRO_CLUSTERS.keys()), (
    "VAD 매핑과 kote_classifier의 클러스터 정의가 불일치합니다. "
    "클러스터를 추가/변경했다면 이 표도 함께 갱신하세요."
)

MAX_EMOTION_DELTA = 8.0   # processor.py 기존 crisis 보정폭(+8)과 동일 스케일
MAX_ENERGY_DELTA = 8.0
AROUSAL_BASELINE = 0.5    # 이 값 기준으로 각성도가 높으면 에너지 상승, 낮으면 하강으로 해석
MIN_ACTIVATION = 1e-4     # 전체 클러스터 확률 합이 0에 가까울 때 0-division 방지


def compute_vad_deltas(cluster_probs: Dict[str, float]) -> Tuple[float, float]:
    """
    cluster_probs: kote_classifier.analyze()의 cluster_probs (클러스터명: 확률[0~1])
    반환: (emotion_delta, energy_delta) - state_service.update()에 그대로 전달

    방식: 클러스터 확률을 가중치로 사용한 valence/arousal 가중평균을 구한 뒤,
    각각 emotion_delta/energy_delta 스케일로 변환.
    (sigmoid 멀티라벨 특성상 클러스터 확률의 합이 1이 아니므로 총 활성도로 정규화)
    """
    total_activation = sum(cluster_probs.values())
    if total_activation < MIN_ACTIVATION:
        return 0.0, 0.0

    weighted_valence = sum(
        p * CLUSTER_VAD[c]["valence"] for c, p in cluster_probs.items()
    ) / total_activation
    weighted_arousal = sum(
        p * CLUSTER_VAD[c]["arousal"] for c, p in cluster_probs.items()
    ) / total_activation

    emotion_delta = MAX_EMOTION_DELTA * weighted_valence
    # arousal(0~1)을 baseline 기준 -1~1로 정규화 후 스케일
    energy_delta = MAX_ENERGY_DELTA * (weighted_arousal - AROUSAL_BASELINE) * 2

    return float(emotion_delta), float(energy_delta)