import io
import wave
import os
import shutil
from app.config import settings
from app.services.xtts_engine import XTTSEngine

"""
TTS 서비스.
  - standard: 기본 합성 음성
  - family_voice: 사전 등록된 가족 음성 샘플로 클로닝된 음성 사용 (사용자가 켜고 끌 수 있는 옵트인 기능)

TODO: 실제 TTS 엔진 연동 (예: ElevenLabs, Coqui TTS, Azure/Naver Clova 등) - 모델 선정 논의 필요.
지금은 인터페이스만 잡아두고, 엔진이 정해지면 _synthesize_* 메서드 내부만 교체하면 됨.
"""

class TTSService:

    def __init__(self):
        self.xtts = None

        os.makedirs(
        settings.voice_storage_dir,
        exist_ok=True,
        )

    def _get_xtts(self):
        if self.xtts is None:
            self.xtts = XTTSEngine()
        return self.xtts

    def synthesize(
        self,
        text: str,
        use_family_voice: bool = False,
        voice_model_id: str = None,
    ) -> bytes:
        if use_family_voice and voice_model_id:
            return self._synthesize_family_voice(text, voice_model_id)
        return self._synthesize_standard(text)

    def _synthesize_standard(self, text: str) -> bytes:
        # Development fallback: return a short valid WAV so the app can test playback
        # before a real TTS provider is wired in.
        return self._make_silent_wav()

    def _synthesize_family_voice(
        self,
        text: str,
        voice_model_id: str,
    ) -> bytes:

        speaker_path = os.path.join(
            settings.voice_storage_dir,
            voice_model_id,
        )

        if not os.path.exists(speaker_path):
            return self._make_silent_wav()

        return self._get_xtts().synthesize(
            text=text,
            speaker_wav=speaker_path,
            language="ko",
        )

    def register_family_voice(
        self,
        user_id: int,              # 추가
        sample_audio_path: str,
    ) -> str:

        ext = os.path.splitext(
            sample_audio_path
        )[1]

        file_name = f"user_{user_id}{ext}"

        save_path = os.path.join(
            settings.voice_storage_dir,
            file_name,
        )

        shutil.copy(
            sample_audio_path,
            save_path,
        )

        return file_name

    def _make_silent_wav(self, duration_seconds: float = 0.4, sample_rate: int = 16000) -> bytes:
        frames = int(duration_seconds * sample_rate)
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frames)

        return buffer.getvalue()


tts_service = TTSService()
