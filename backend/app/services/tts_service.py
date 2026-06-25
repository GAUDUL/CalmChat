import io
import wave
"""
TTS 서비스.
  - standard: 기본 합성 음성
  - family_voice: 사전 등록된 가족 음성 샘플로 클로닝된 음성 사용 (사용자가 켜고 끌 수 있는 옵트인 기능)

TODO: 실제 TTS 엔진 연동 (예: ElevenLabs, Coqui TTS, Azure/Naver Clova 등) - 모델 선정 논의 필요.
지금은 인터페이스만 잡아두고, 엔진이 정해지면 _synthesize_* 메서드 내부만 교체하면 됨.
"""

class TTSService:
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

    def _synthesize_family_voice(self, text: str, voice_model_id: str) -> bytes:
        # Family-voice cloning is a future provider integration; keep the API shape stable.
        return self._make_silent_wav()

    def register_family_voice(self, sample_audio_path: str) -> str:
        # Placeholder until a voice cloning provider returns a persistent voice model id.
        raise NotImplementedError("Family voice registration is not implemented yet")

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
