"""
backend/test_engine.py

engine.extract(text) -> processor.process_message() 로 이어지는 전체 파이프라인의
핵심부(engine.extract)만 독립적으로 검증한다. DB 없이 순수하게 텍스트 -> delta 변환만 확인.

실행:
    cd backend
    "<venv>/bin/python" test_engine.py
"""

from app.services.emotion.engine import EmotionEngine

engine = EmotionEngine()

# [테스트 케이스 설계 근거]
# - 각 매크로 클러스터(긍정_기쁨/긍정_안정/슬픔_상실/자기지향_부정/불안_긴장/분노_짜증/당황_혼란)를
#   대표하는 문장을 하나씩 배치해, emotion_delta의 부호(+/-)와 대략적 크기가 말이 되는지 확인.
# - 자기지향_부정 계열 문장 2개(죄책감 vs 열등감)를 따로 넣어 Gemini 보조판단 트리거 여부를 확인.
# - crisis 키워드 문장 1개로 안전 레이어(-8/-4 페널티)가 정상 작동하는지 확인.
TEST_CASES = [
    ("오늘 정말 행복하고 즐거운 하루였어요", "긍정_기쁨 기대 (emotion_delta > 0)"),
    ("요즘 마음이 편안하고 안정적이에요", "긍정_안정 기대 (emotion_delta > 0)"),
    ("요즘 너무 슬프고 눈물이 나요", "슬픔_상실 기대 (emotion_delta < 0)"),
    ("내가 잘못해서 미안하고 계속 후회돼요", "자기지향_부정(죄책감) 기대 - Gemini 보조판단 트리거 확인"),
    ("나 자신이 너무 한심하고 열등감이 느껴져요", "자기지향_부정(열등감) 기대 - KOTE 자체 신호 확인"),
    ("요즘 불안하고 걱정이 많아요", "불안_긴장 기대 (energy_delta 상승 가능성)"),
    ("너무 짜증나고 화가 나요", "분노_짜증 기대"),
    ("당황스럽고 혼란스러워요", "당황_혼란 기대"),
    ("죽고 싶다는 생각이 들어요", "crisis_keyword_flag=True 기대, emotion_delta에 -8 페널티 포함"),
    ("드라마에서 죽고 싶다는 대사가 나왔어요", "crisis 컨텍스트 억제 기대 (crisis_keyword_flag=False)"),
]


def main():
    for text, expectation in TEST_CASES:
        print("=" * 70)
        print(f"입력: {text}")
        print(f"기대: {expectation}")
        result = engine.extract(text)
        print(f"  emotion_delta: {result['emotion_delta']:.3f}")
        print(f"  energy_delta: {result['energy_delta']:.3f}")
        print(f"  health_keyword_flag: {result['health_keyword_flag']}")
        print(f"  crisis_keyword_flag: {result['crisis_keyword_flag']}")
        print(f"  danger_confidence: {result['danger_confidence']}")
        print(f"  guilt_regret_llm_checked: {result['guilt_regret_llm_checked']}")
        print(f"  guilt_regret_llm_result: {result['guilt_regret_llm_result']}")
        top_clusters = sorted(
            result["cluster_probs"].items(), key=lambda kv: kv[1], reverse=True
        )[:3]
        print(f"  top3 클러스터: {top_clusters}")


if __name__ == "__main__":
    main()