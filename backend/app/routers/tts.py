from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import FamilyVoice
from app.routers.users import get_user_or_404
from app.schemas.schemas import TTSRequest
from app.services.tts_service import tts_service

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("")
async def text_to_speech(payload: TTSRequest, db: Session = Depends(get_db)):
    get_user_or_404(db, payload.user_id)

    voice_model_id = None
    if payload.use_family_voice:
        family_voice = (
            db.query(FamilyVoice)
            .filter(FamilyVoice.user_id == payload.user_id)
            .first()
        )
        voice_model_id = family_voice.voice_model_id if family_voice else None

    audio_bytes = tts_service.synthesize(
        text=payload.text,
        use_family_voice=payload.use_family_voice,
        voice_model_id=voice_model_id,
    )
    return Response(content=audio_bytes, media_type="audio/wav")
