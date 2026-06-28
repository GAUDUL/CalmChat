import os
import tempfile
from TTS.api import TTS
from app.config import settings


class XTTSEngine:
    def __init__(self):
        self.model = TTS(
            model_name=settings.xtts_model_name
        )

    def synthesize(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ko",
    ) -> bytes:

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as tmp:
            output_path = tmp.name

        try:
            self.model.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                file_path=output_path,
            )

            with open(output_path, "rb") as f:
                return f.read()

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)