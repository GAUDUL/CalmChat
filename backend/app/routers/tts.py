from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import FamilyVoice
from app.schemas.schemas import TTSRequest
from app.services.tts_service import tts_service

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("")
async def text_to_speech(payload: TTSRequest, db: Session = Depends(get_db)):
    """프론트: 응답 텍스트 -> POST /tts -> TTS 모델 -> 오디오 스트림 반환"""
    voice_model_id = None
    if payload.use_family_voice:
        fv = db.query(FamilyVoice).filter(FamilyVoice.user_id == payload.user_id).first()
        voice_model_id = fv.voice_model_id if fv else None

    audio_bytes = tts_service.synthesize(
        text=payload.text,
        use_family_voice=payload.use_family_voice,
        voice_model_id=voice_model_id,
    )
    return Response(content=audio_bytes, media_type="audio/wav")
