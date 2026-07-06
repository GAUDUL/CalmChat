"""
TTS 서비스.
  - standard: 기본 합성 음성 (ElevenLabs)
  - family_voice: 사전 등록된 가족 음성 샘플로 클로닝된 음성 사용
"""
import os
import requests
import shutil
import uuid

VOICE_DIR = "uploads/family_voices"

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George (무료 플랜)
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

class TTSService:
    def synthesize(self, text: str, use_family_voice: bool = False, reference_audio_path: str = None) -> bytes:
        if use_family_voice and reference_audio_path:
            return self._synthesize_family_voice(text, reference_audio_path)
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

    def _synthesize_family_voice(self, text: str, sample_audio_path: str) -> bytes:
        response = requests.post(
                f"{TTS_SERVICE_URL}/synthesize",
                json={
                    "text": text,
                    "sample_audio_path": sample_audio_path,
                },
                timeout=60,
            )

        response.raise_for_status()
        return response.content

    def register_family_voice(self, sample_audio_path: str) -> str:
        os.makedirs(VOICE_DIR, exist_ok=True)

        filename = f"{uuid.uuid4()}.wav"
        saved_path = os.path.join(VOICE_DIR, filename)
        shutil.copy(sample_audio_path, saved_path)

        response = requests.post(
            f"{TTS_SERVICE_URL}/register",
            json={"sample_audio_path": saved_path},
            timeout=120,
        )
        response.raise_for_status()
        embedding_path = response.json()["embedding_path"]

        return saved_path, embedding_path

tts_service = TTSService()