import json
from pathlib import Path


EMOTION_RULES = {
    "negative": {
        "sad": -2,
        "depressed": -2.5,
        "down": -1.5,
        "anxious": -2,
        "stressed": -2,
        "overwhelmed": -2.5,
        "lonely": -2,
        "frustrated": -1.5,
        "tired of": -2,
        "슬퍼": -2,
        "우울": -2.5,
        "불안": -2,
        "걱정": -1.5,
        "답답": -1.5,
        "짜증": -1.5,
        "외로": -2,
        "재미없": -2.5,
        "재미가 없": -2.5,
        "흥미가 없": -2.5,
        "의욕이 없": -2,
        "아무것도 하기 싫": -2.5,
        "무기력": -2.5,
        "쓸모없": -2.5,
        "희망이 없": -2.5,
    },
    "positive": {
        "happy": 2,
        "good": 1,
        "great": 2,
        "relaxed": 1.5,
        "calm": 1.5,
        "better": 1.5,
        "excited": 2,
        "행복": 2,
        "좋아": 1,
        "좋다": 1,
        "괜찮": 1,
        "편안": 1.5,
        "차분": 1.5,
        "나아졌": 1.5,
        "즐거": 2,
        "기쁘": 2,
        "고마": 1,
    },
}

ENERGY_RULES = {
    "negative": {
        "tired": -2,
        "exhausted": -2.5,
        "fatigued": -2,
        "sleepy": -1.5,
        "no energy": -2.5,
        "pain": -2,
        "headache": -1.5,
        "back pain": -1.5,
        "burned out": -2.5,
        "피곤": -2,
        "지쳤": -2,
        "지침": -2,
        "기운이 없": -2.5,
        "기운이 하나도 없": -3,
        "기운 하나도 없": -3,
        "힘이 없": -2.5,
        "힘들": -2,
        "졸려": -1.5,
        "몸이 무거": -1.5,
        "아파": -2,
        "아프": -2,
        "두통": -1.5,
        "허리": -1.5,
        "무릎": -1.5,
        "몸살": -2,
    },
    "positive": {
        "energetic": 2,
        "active": 1.5,
        "worked out": 2,
        "went for a walk": 1.5,
        "feeling strong": 1.5,
        "기운 나": 2,
        "운동": 2,
        "산책": 1.5,
        "걸었": 1.5,
        "힘이 나": 1.5,
    },
}

PHRASE_RULES = [
    ("not myself", -2),
    ("feeling off", -1.5),
    ("getting worse", -2),
    ("getting better", 1.5),
    ("i'm fine", 0.5),
    ("내가 내가 아닌 것 같아", -2),
    ("몸이 이상", -1.5),
    ("컨디션이 안 좋아", -1.5),
    ("점점 나빠", -2),
    ("조금 나아", 1.5),
    ("괜찮아졌", 1.5),
    ("사는 게 재미없", -2.5),
    ("하루가 의미 없", -2.5),
    ("밖에 나가기 싫", -1.5),
    ("사람 만나기 싫", -1.5),
    ("잠을 못 잤", -1.5),
]

NEGATION_TERMS = {
    "안",
    "못",
    "아니",
    "않",
    "없",
    "no",
    "not",
    "never",
}

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

HEALTH_KEYWORD_RULES = {
    "chest pain",
    "short of breath",
    "hard to breathe",
    "dizzy",
    "fainted",
    "fell down",
    "blood pressure",
    "diabetes",
    "fever",
    "vomit",
    "diarrhea",
    "hospital",
    "medicine",
    "가슴 통증",
    "가슴이 아",
    "숨이 차",
    "숨쉬기 힘",
    "호흡 곤란",
    "어지러",
    "기절",
    "쓰러졌",
    "넘어졌",
    "혈압",
    "혈당",
    "고열",
    "구토",
    "설사",
    "응급",
    "119",
}

HEALTH_CONTEXT_SUPPRESS_RULES = {
    "아프지 않",
    "아픈 건 아니",
    "통증은 없",
    "숨이 차지 않",
    "괜찮아",
    "괜찮아요",
    "약 먹었",
    "뉴스에서",
    "드라마에서",
    "친구가",
    "not in pain",
    "no pain",
    "not dizzy",
    "not short of breath",
    "already went",
    "saw a doctor",
    "took medicine",
}


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
    EMOTION_RULES["negative"].update(overrides.get("emotion_negative", {}))
    EMOTION_RULES["positive"].update(overrides.get("emotion_positive", {}))
    ENERGY_RULES["negative"].update(overrides.get("energy_negative", {}))
    ENERGY_RULES["positive"].update(overrides.get("energy_positive", {}))
    CRISIS_KEYWORD_RULES.update(overrides.get("crisis_keywords", []))
    HEALTH_KEYWORD_RULES.update(overrides.get("health_keywords", []))
    CRISIS_CONTEXT_SUPPRESS_RULES.update(overrides.get("crisis_suppressors", []))
    HEALTH_CONTEXT_SUPPRESS_RULES.update(overrides.get("health_suppressors", []))


_apply_keyword_overrides()
