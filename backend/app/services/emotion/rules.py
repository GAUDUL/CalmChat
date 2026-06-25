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
    },
    "positive": {
        "happy": +2,
        "good": +1,
        "great": +2,
        "relaxed": +1.5,
        "calm": +1.5,
        "better": +1.5,
        "excited": +2,
    }
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
    },
    "positive": {
        "energetic": +2,
        "active": +1.5,
        "worked out": +2,
        "went for a walk": +1.5,
        "feeling strong": +1.5,
    }
}

PHRASE_RULES = [
    ("not myself", -2),
    ("feeling off", -1.5),
    ("getting worse", -2),
    ("getting better", +1.5),
    ("i'm fine", +0.5),
]