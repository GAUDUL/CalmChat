"""
STT 서비스 (OpenAI Whisper 래핑).

TODO (★ 사투리 파인튜닝):
  1. 농촌 노인 방언 음성+전사 데이터셋 수집/라벨링 (확보 방안 별도 논의)
  2. Whisper fine-tune 수행 후 가중치를 settings.whisper_finetuned_checkpoint 경로에 저장
  3. load_model()이 fine-tuned checkpoint를 우선 로드하도록 되어 있음 (아래 구현 참고)
"""
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
    def transcribe(cls, audio_path: str, language: str = "ko") -> dict:
        model = cls.load_model()
        result = model.transcribe(audio_path, language=language)
        return {
            "text": result.get("text", "").strip(),
            "confidence": None,  # whisper는 단일 confidence를 기본 제공하지 않음 -> 필요시 avg_logprob 활용
        }


stt_service = STTService()
