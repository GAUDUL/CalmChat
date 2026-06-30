import whisper

from app.config import settings


class STTService:
    _model = None

    @classmethod
    def load_model(cls):
        if cls._model is None:
            checkpoint = settings.whisper_finetuned_checkpoint or settings.whisper_model_size
            cls._model = whisper.load_model(checkpoint)
        return cls._model

    @classmethod
    def transcribe(cls, audio_path: str, language: str | None = None) -> dict:
        model = cls.load_model()
        result = model.transcribe(audio_path, language=language)
        return {
            "text": result.get("text", "").strip(),
            # Whisper does not expose a single confidence score by default.
            "confidence": None,
        }


stt_service = STTService()
