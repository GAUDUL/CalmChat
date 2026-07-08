"""
app/services/emotion/vad_scoring.py

8개 매크로 클러스터 확률 -> emotion_delta 변환 (점수화 단계).

[energy 제거 - 2026-07]
energy는 별도로 점수화하지 않기로 확정되어, 기존 arousal 기반 energy_delta
계산 로직을 전부 제거함. 이제 valence만으로 emotion_delta를 산출한다.

[중요 - 팀 리뷰 필요]
아래 CLUSTER_VALENCE 좌표는 Russell의 circumplex model을 참고한 1차 초안값이다.
게이미피케이션/스코어링 담당(임수현)과 스케일 및 의미를 맞춘 뒤 최종 확정할 것.
지금 값 그대로 프로덕션에 반영하지 말 것.

state_service.py의 EmotionStateService.update()가 emotion_delta를 받아
기존 점수에 누적하는 구조이므로, 이 델타값은 "이번 대화 turn 하나가 전체
점수에 미치는 변화폭"으로 해석된다. processor.py의 기존 crisis 보정치(+8)와
스케일을 맞추기 위해 MAX_EMOTION_DELTA를 8.0으로 설정함.
"""

from typing import Dict

from .kote_classifier import MACRO_CLUSTERS

# Valence: -1(부정) ~ +1(긍정). arousal/dominance는 energy 스코어링 폐지로 더 이상 사용하지 않음.
CLUSTER_VALENCE = {
    "긍정_기쁨":     0.9,
    "긍정_안정":     0.7,
    "슬픔_상실":     -0.7,
    "자기지향_부정": -0.6,
    "불안_긴장":     -0.5,
    "분노_짜증":     -0.6,
    "당황_혼란":     -0.2,
    "기타_중립":     0.0,
}

assert set(CLUSTER_VALENCE.keys()) == set(MACRO_CLUSTERS.keys()), (
    "VALENCE 매핑과 kote_classifier의 클러스터 정의가 불일치합니다. "
    "클러스터를 추가/변경했다면 이 표도 함께 갱신하세요."
)

MAX_EMOTION_DELTA = 8.0   # processor.py 기존 crisis 보정폭(+8)과 동일 스케일
MIN_ACTIVATION = 1e-4     # 전체 클러스터 확률 합이 0에 가까울 때 0-division 방지


def compute_emotion_delta(cluster_probs: Dict[str, float]) -> float:
    """
    cluster_probs: kote_classifier.analyze()의 cluster_probs (클러스터명: 확률[0~1])
    반환: emotion_delta - state_service.update()에 그대로 전달

    방식: 클러스터 확률을 가중치로 사용한 valence 가중평균을 구한 뒤
    emotion_delta 스케일로 변환.
    (sigmoid 멀티라벨 특성상 클러스터 확률의 합이 1이 아니므로 총 활성도로 정규화)
    """
    total_activation = sum(cluster_probs.values())
    if total_activation < MIN_ACTIVATION:
        return 0.0

    weighted_valence = sum(
        p * CLUSTER_VALENCE[c] for c, p in cluster_probs.items()
    ) / total_activation

    return float(MAX_EMOTION_DELTA * weighted_valence)