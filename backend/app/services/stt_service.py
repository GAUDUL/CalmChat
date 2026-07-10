from app.config import settings
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch
import librosa

class STTService:
    _model = None
    _processor = None
    _device = "cuda" if torch.cuda.is_available() else "cpu"

    @classmethod
    def load_model(cls):
        if cls._model is None:
            checkpoint = (
                settings.whisper_finetuned_checkpoint
                or settings.whisper_model_size
            )
            
            cls._processor = WhisperProcessor.from_pretrained(checkpoint)
            cls._model = WhisperForConditionalGeneration.from_pretrained(checkpoint)
            cls._model.to(cls._device)
            cls._model.eval()

        return cls._model, cls._processor

    @classmethod
    def transcribe(cls, audio_path: str, language: str | None = None) -> dict:
        model, processor  = cls.load_model()
        # Whisper는 16kHz mono 입력 사용
        audio, _ = librosa.load(audio_path, sr=16000)

        input_features = processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
        ).input_features.to(cls._device)

        predicted_ids = model.generate(
            input_features,
            language=language,
            task="transcribe",
        )

        text = processor.batch_decode(
            predicted_ids,
            skip_special_tokens=True,
        )[0]

        return {
            "text": text.strip(),
            "confidence": None,
        }


stt_service = STTService()
