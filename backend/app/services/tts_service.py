"""
TTS 서비스.
  - standard: 기본 합성 음성 (ElevenLabs)
  - family_voice: 사전 등록된 가족 음성 샘플로 클로닝된 음성 사용
"""
import os
import requests

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George (무료 플랜)
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

class TTSService:
    def synthesize(self, text: str, use_family_voice: bool = False, voice_model_id: str = None) -> bytes:
        if use_family_voice and voice_model_id:
            return self._synthesize_family_voice(text, voice_model_id)
        return self._synthesize_standard(text)

    def _synthesize_standard(self, text: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.7,
                "similarity_boost": 0.8,
                "speed": 0.9
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content

    def _synthesize_family_voice(self, text: str, voice_model_id: str) -> bytes:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_model_id}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.7,
                "similarity_boost": 0.8,
                "speed": 0.9
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content

    def register_family_voice(self, sample_audio_path: str) -> str:
        """가족 목소리 샘플 업로드 -> voice_model_id 발급"""
        url = "https://api.elevenlabs.io/v1/voices/add"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        with open(sample_audio_path, "rb") as f:
            files = {"files": f}
            data = {"name": "family_voice"}
            response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json()["voice_id"]

tts_service = TTSService()