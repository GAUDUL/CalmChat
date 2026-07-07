import json
from pathlib import Path

CRISIS_KEYWORD_RULES = {
    # Treat suicide/self-harm language as a separate safety signal.
    "suicide",
    "kill myself",
    "end my life",
    "hurt myself",
    "self harm",
    "self-harm",
    "don't want to live",
    "want to die",
    "죽고 싶",
    "죽고싶",
    "자살",
    "자해",
    "나를 해치",
    "그만 살",
    "삶을 끝",
}

CRISIS_CONTEXT_SUPPRESS_RULES = {
    "뉴스에서",
    "드라마에서",
    "영화에서",
    "소설에서",
    "친구가 말했",
    "not me",
    "not about me",
}

# Health/emergency physical-symptom language, kept separate from crisis
# (self-harm) keywords so the two safety signals can be tracked and
# confirmed independently in chat.py / engine.py.
HEALTH_KEYWORD_RULES = {
    "chest pain",
    "short of breath",
    "hard to breathe",
    "can't breathe",
    "119",
    "가슴 통증",
    "가슴이 아프",
    "호흡 곤란",
    "숨쉬기 힘",
    "숨이 차",
    "쓰러졌",
    "의식을 잃",
}

KOTE_LABELS = [
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

def _load_keyword_overrides() -> dict:
    rules_path = Path(__file__).with_name("keyword_rules.json")
    if not rules_path.exists():
        return {}

    try:
        return json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _apply_keyword_overrides() -> None:
    overrides = _load_keyword_overrides()
    CRISIS_KEYWORD_RULES.update(overrides.get("crisis_keywords", []))
    CRISIS_CONTEXT_SUPPRESS_RULES.update(overrides.get("crisis_suppressors", []))
    HEALTH_KEYWORD_RULES.update(overrides.get("health_keywords", []))


_apply_keyword_overrides()