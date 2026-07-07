import json
import os
import re
import random
import librosa
import torch
from torch.utils.data import Dataset
from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    TrainerCallback,
    WhisperForConditionalGeneration,
    WhisperProcessor,
)

# ----------------------------------------------------------------------------
# 경로 설정
# ----------------------------------------------------------------------------
BASE_DIR = os.path.expanduser(
    "~/Desktop/1_Project/0_충북대학교 석사 1학기/4_학회/260406_ICCAS/CalmChat/"
    "notebooks/139-1.중·노년층 한국어 방언 데이터 (강원도, 경상도)"
)

audio_dir = os.path.join(BASE_DIR, "Training", "01.원천데이터")
label_dir = os.path.join(BASE_DIR, "Training", "02.라벨링데이터")

model_out_dir = os.path.expanduser("~/dialect_data/model/whisper-dialect")
os.makedirs(model_out_dir, exist_ok=True)

SUBSET_SIZE = 60000  # None이면 전체 사용
MAX_LABEL_LEN = 448

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"


def log(msg):
    print(msg, flush=True)


def main():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    log(f"사용 디바이스: {device}")

    # ------------------------------------------------------------------
    # 파일 목록 수집 (하위 폴더까지 재귀 탐색)
    # ------------------------------------------------------------------
    audio_files = []
    for root, _, files in os.walk(audio_dir):
        for f in files:
            if f.endswith(".wav"):
                audio_files.append(os.path.join(root, f))

    label_files = []
    for root, _, files in os.walk(label_dir):
        for f in files:
            if f.endswith(".json"):
                label_files.append(os.path.join(root, f))

    log(f"오디오 파일 수: {len(audio_files)}")
    log(f"라벨 파일 수: {len(label_files)}")

    def norm_key(path):
        stem = os.path.splitext(os.path.basename(path))[0]
        return re.sub(r"^[a-zA-Z]+_", "", stem, count=1)

    label_index = {norm_key(p): p for p in label_files}

    def build_index(audio_paths, label_index):
        items = []
        skipped = []
        for audio_path in sorted(audio_paths):
            label_path = label_index.get(norm_key(audio_path))
            if not label_path:
                continue
            try:
                with open(label_path, "r", encoding="utf-8") as f:
                    label_data = json.load(f)
                text = label_data["transcription"]["standard"]
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                skipped.append((label_path, str(e)))
                continue
            items.append({"audio_path": audio_path, "text": text})

        log(f"인덱싱된 데이터 수: {len(items)}")
        log(f"스킵된(손상/구조 다른) 라벨 수: {len(skipped)}")
        for path, err in skipped[:5]:
            log(f" - {path}\n   {err}")
        return items

    dataset_index = build_index(audio_files, label_index)

    random.seed(42)
    if SUBSET_SIZE and SUBSET_SIZE < len(dataset_index):
        dataset_index = random.sample(dataset_index, SUBSET_SIZE)
        log(f"랜덤 서브셋 적용: {len(dataset_index)}개")

    # ------------------------------------------------------------------
    # 모델/프로세서 로드
    # ------------------------------------------------------------------
    processor = WhisperProcessor.from_pretrained("openai/whisper-small")
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-small")
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    log("모델 로드 완료")

    # ------------------------------------------------------------------
    # Dataset / collate_fn
    # ------------------------------------------------------------------
    class DialectDataset(Dataset):
        def __init__(self, items, processor):
            self.items = items
            self.processor = processor

        def __len__(self):
            return len(self.items)

        def __getitem__(self, idx):
            item = self.items[idx]
            speech, _ = librosa.load(item["audio_path"], sr=16000)
            inputs = self.processor(speech, sampling_rate=16000, return_tensors="pt")
            input_features = inputs.input_features[0]

            labels = self.processor.tokenizer(
                item["text"],
                return_tensors="pt",
                truncation=True,
                max_length=MAX_LABEL_LEN,
            ).input_ids[0]

            return {"input_features": input_features, "labels": labels}

    train_dataset = DialectDataset(dataset_index, processor)
    log(f"데이터셋 크기: {len(train_dataset)}")

    def collate_fn(batch):
        input_features = torch.stack([item["input_features"] for item in batch])
        label_list = [item["labels"] for item in batch]
        padded_labels = torch.full((len(label_list), MAX_LABEL_LEN), -100, dtype=torch.long)
        for i, label in enumerate(label_list):
            length = min(label.size(0), MAX_LABEL_LEN)
            padded_labels[i, :length] = label[:length]
        return {"input_features": input_features, "labels": padded_labels}

    class MPSCacheClearCallback(TrainerCallback):
        def on_step_end(self, args, state, control, **kwargs):
            if state.global_step % 50 == 0 and torch.backends.mps.is_available():
                torch.mps.empty_cache()

    # ------------------------------------------------------------------
    # 학습 설정
    # ------------------------------------------------------------------
    training_args = Seq2SeqTrainingArguments(
        output_dir=model_out_dir,
        num_train_epochs=1,
        per_device_train_batch_size=8,
        dataloader_num_workers=0,
        dataloader_pin_memory=False,
        learning_rate=1e-5,
        save_steps=500,
        save_total_limit=3,
        logging_steps=20,
        predict_with_generate=True,
        fp16=False,
        report_to="none",
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=collate_fn,
        processing_class=processor.feature_extractor,
        callbacks=[MPSCacheClearCallback()],
    )

    # 이전 체크포인트가 있으면 자동으로 이어서 학습
    last_checkpoint = None
    if os.path.isdir(model_out_dir):
        checkpoints = [d for d in os.listdir(model_out_dir) if d.startswith("checkpoint-")]
        if checkpoints:
            last_checkpoint = os.path.join(
                model_out_dir,
                sorted(checkpoints, key=lambda x: int(x.split("-")[1]))[-1],
            )
            log(f"체크포인트 발견, 이어서 학습: {last_checkpoint}")

    log("학습 시작!")
    trainer.train(resume_from_checkpoint=last_checkpoint)
    log("학습 완료!")

    model.save_pretrained(model_out_dir)
    processor.save_pretrained(model_out_dir)
    log(f"모델 저장 완료! -> {model_out_dir}")


if __name__ == "__main__":
    main()
