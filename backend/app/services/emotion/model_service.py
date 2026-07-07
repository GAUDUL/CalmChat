import os

import torch

from .rules import KOTE_LABELS

# TODO: point this at the actual fine-tuned checkpoint (repo id or local path).
# Kept overridable via env var so it doesn't need a code change per environment.
EMOTION_MODEL_NAME = os.environ.get("EMOTION_MODEL_NAME", "REPLACE_WITH_ACTUAL_MODEL_NAME")

_model = None
_tokenizer = None


def _load_default_model():
    global _model, _tokenizer

    if _model is None or _tokenizer is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(EMOTION_MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(EMOTION_MODEL_NAME)
        _model.eval()
    return _model, _tokenizer


class ModelService:

    def __init__(
        self,
        model=None,
        tokenizer=None,
    ):
        # Allows `ModelService()` with no args (used by EmotionEngine's default
        # construction) while still supporting injection for tests.
        if model is None or tokenizer is None:
            model, tokenizer = _load_default_model()
        self.model = model
        self.tokenizer = tokenizer

    # 가장 강한 강도
    def _calculate_intensity(self, emotions):

        if not emotions:
            return 0
        
        return max( e["score"] for e in emotions )

    def _negative_score(self, emotions):

        negative_labels = {
            "슬픔",
            "불안/걱정",
            "화남/분노",
            "서러움",
            "공포/무서움",
            "절망"
        }

        score = 0
        for e in emotions:
            if e["label"] in negative_labels:
                score += e["score"]

        return min(score, 1.0)

    def _positive_score(self, emotions):

        positive_labels = {
            "기쁨",
            "행복",
            "즐거움/신남",
            "안심/신뢰"
        }

        score = 0
        for e in emotions:
            if e["label"] in positive_labels:
                score += e["score"]

        return min(score, 1.0)
    
    def predict_emotion(self, text):
        
        THRESHOLD = 0.3
        TOP_K = 5

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        with torch.no_grad():
            logits = self.model(**inputs).logits

        probs = torch.sigmoid(logits)[0].cpu().numpy()

        results = []

        for idx, prob in enumerate(probs):
            results.append({
                "label": KOTE_LABELS[idx],
                "score": float(prob)
            })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        results = results[:TOP_K]
        results = [
            r for r in results
            if r["score"] >= THRESHOLD
        ]

        return results

    def predict(self, text):

        emotions = self.predict_emotion(text)

        dominant = (
            emotions[0]["label"]
            if emotions
            else None
        )

        return {
            "dominant": dominant,
            "intensity": self._calculate_intensity(emotions),
            "positive_score": self._positive_score(emotions),
            "negative_score": self._negative_score(emotions),
            "emotions": emotions,
        }