import os
import shutil
import tempfile

from fastapi import APIRouter, File, UploadFile

from app.schemas.schemas import STTResponse
from app.services.stt_service import stt_service

router = APIRouter(prefix="/stt", tags=["STT"])

# 테스트용 (현재 사용 X)
@router.post("", response_model=STTResponse)
def speech_to_text(audio: UploadFile = File(...)):
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name
        # STT 수행
        result = stt_service.transcribe(tmp_path)
        return STTResponse(**result)
    finally:
        # 임시 파일 정리
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
