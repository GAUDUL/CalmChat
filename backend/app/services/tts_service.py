"""
TTS 서비스.
  - standard: 기본 합성 음성
  - family_voice: 사전 등록된 가족 음성 샘플로 클로닝된 음성 사용 (사용자가 켜고 끌 수 있는 옵트인 기능)

TODO: 실제 TTS 엔진 연동 (예: ElevenLabs, Coqui TTS, Azure/Naver Clova 등) - 모델 선정 논의 필요.
지금은 인터페이스만 잡아두고, 엔진이 정해지면 _synthesize_* 메서드 내부만 교체하면 됨.
"""


class TTSService:
    def synthesize(self, text: str, use_family_voice: bool = False, voice_model_id: str = None) -> bytes:
        if use_family_voice and voice_model_id:
            return self._synthesize_family_voice(text, voice_model_id)
        return self._synthesize_standard(text)

    def _synthesize_standard(self, text: str) -> bytes:
        # TODO: 표준 TTS 엔진 호출
        raise NotImplementedError("표준 TTS 엔진 연동 필요")

    def _synthesize_family_voice(self, text: str, voice_model_id: str) -> bytes:
        # TODO: voice_model_id로 등록된 가족 목소리 클로닝 모델 호출
        raise NotImplementedError("가족 음성 합성 엔진 연동 필요")

    def register_family_voice(self, sample_audio_path: str) -> str:
        """가족 목소리 샘플 업로드 -> voice_model_id 발급 (클로닝 서비스 연동 자리)."""
        # TODO: 클로닝 서비스에 업로드 후 model_id 반환
        raise NotImplementedError("가족 목소리 등록 로직 구현 필요")


tts_service = TTSService()
