import os
from app.config import settings


class TTSService:
    def __init__(self):
        pass

    def synthesize(self, text: str, use_family_voice: bool = False, voice_id: str | None = None) -> bytes:
        if not voice_id:
            voice_id = settings.elevenlabs_default_voice_id

        return self._call_elevenlabs(text, voice_id)


tts_service = TTSService()
