import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File
from app.services.stt_service import stt_service
from app.schemas.schemas import STTResponse

router = APIRouter(prefix="/stt", tags=["STT"])


@router.post("", response_model=STTResponse)
async def speech_to_text(audio: UploadFile = File(...)):
    """프론트: 음성 입력 시작 -> POST /stt -> Whisper STT -> 텍스트 반환"""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    result = stt_service.transcribe(tmp_path)
    return STTResponse(**result)
