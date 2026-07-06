"""
OpenVoice V2 추론 엔진.
서버 시작 시 한 번만 로드하고, 이후 요청마다 재사용합니다.
"""
import os
import uuid

import torch
from melo.api import TTS
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
from huggingface_hub import snapshot_download
import os

CHECKPOINT_DIR = os.getenv("OPENVOICE_CHECKPOINT_DIR", "/app/checkpoints_v2")
EMBEDDING_DIR = os.getenv("EMBEDDING_DIR", "/app/uploads/family_voices/embeddings")
TMP_DIR = "/tmp/tts_work"

DEVICE = "cpu"

CHECKPOINT_DIR = os.getenv(
    "OPENVOICE_CHECKPOINT_DIR",
    "/app/checkpoints_v2",
)

def ensure_openvoice_checkpoints():
    required_files = [
        os.path.join(
            CHECKPOINT_DIR,
            "converter",
            "checkpoint.pth",
        ),
        os.path.join(
            CHECKPOINT_DIR,
            "converter",
            "config.json",
        ),
        os.path.join(
            CHECKPOINT_DIR,
            "base_speakers",
            "ses",
            "kr.pth",
        ),
    ]

    if all(os.path.exists(f) for f in required_files):
        return

    snapshot_download(
        repo_id="myshell-ai/OpenVoiceV2",
        local_dir=CHECKPOINT_DIR,
        local_dir_use_symlinks=False,
    )

class OpenVoiceEngine:
    def __init__(self):
        os.makedirs(EMBEDDING_DIR, exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)

        converter_dir = f"{CHECKPOINT_DIR}/converter"
        self.tone_color_converter = ToneColorConverter(
            f"{converter_dir}/config.json", device=DEVICE
        )
        self.tone_color_converter.load_ckpt(f"{converter_dir}/checkpoint.pth")

        # base speaker (MeloTTS)
        self.base_model = TTS(language="EN", device=DEVICE)
        self.speaker_ids = self.base_model.hps.data.spk2id

        # base speaker의 기준 임베딩 (OpenVoice 체크포인트에 포함)
        self.source_se = torch.load(
            f"{CHECKPOINT_DIR}/base_speakers/ses/kr.pth", map_location=DEVICE
        )

    def extract_embedding(self, sample_audio_path: str) -> str:
        """참조 음성에서 tone color 임베딩을 추출해 파일로 저장하고 경로를 반환합니다."""
        target_se, _ = se_extractor.get_se(
            sample_audio_path, self.tone_color_converter, vad=False
        )

        embedding_path = os.path.join(EMBEDDING_DIR, f"{uuid.uuid4()}.pth")
        torch.save(target_se, embedding_path)
        return embedding_path

    def synthesize(self, text: str, embedding_path: str) -> bytes:
        """텍스트 -> base 음성 생성 -> tone color 변환 -> 오디오 바이트 반환."""
        if not os.path.exists(embedding_path):
            raise FileNotFoundError(f"임베딩 파일을 찾을 수 없습니다: {embedding_path}")

        target_se = torch.load(embedding_path, map_location=DEVICE)

        base_audio_path = os.path.join(TMP_DIR, f"{uuid.uuid4()}.wav")
        output_path = os.path.join(TMP_DIR, f"{uuid.uuid4()}_out.wav")

        try:
            speaker_id = self.speaker_ids["EN"]
            self.base_model.tts_to_file(text, speaker_id, base_audio_path, speed=0.95)

            self.tone_color_converter.convert(
                audio_src_path=base_audio_path,
                src_se=self.source_se,
                tgt_se=target_se,
                output_path=output_path,
            )

            with open(output_path, "rb") as f:
                return f.read()
        finally:
            for p in (base_audio_path, output_path):
                if os.path.exists(p):
                    os.remove(p)

ensure_openvoice_checkpoints()
engine = OpenVoiceEngine()