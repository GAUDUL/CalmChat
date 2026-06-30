import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import FamilyVoice
from app.routers.users import require_user_access
from app.schemas.schemas import FamilyVoiceEnabledRequest, TTSRequest
from app.services.tts_service import tts_service

router = APIRouter(prefix="/tts", tags=["TTS"])

ALLOWED_VOICE_EXTENSIONS = {".wav", ".mp3", ".m4a"}


@router.post("")
def text_to_speech(
    payload: TTSRequest,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    require_user_access(db, payload.user_id, x_device_key)

    voice_id = None

    if payload.use_family_voice:
        family_voice = (
            db.query(FamilyVoice)
            .filter(FamilyVoice.user_id == payload.user_id)
            .first()
        )

        if family_voice:
            voice_id = family_voice.voice_id

    audio_bytes = tts_service.synthesize(
        text=payload.text,
        voice_model_id=voice_id,
        use_family_voice=bool(voice_id),
    )

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/family/upload")
def upload_family_voice(
    user_id: int = Form(...),
    family_member_name: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    require_user_access(db, user_id, x_device_key)

    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    ext = os.path.splitext(audio.filename)[1].lower()
    if ext not in ALLOWED_VOICE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        voice_id = tts_service.register_family_voice(tmp_path)

        family_voice = db.query(FamilyVoice).filter(FamilyVoice.user_id == user_id).first()

        if family_voice:
            family_voice.family_member_name = family_member_name
            family_voice.voice_id = voice_id
        else:
            family_voice = FamilyVoice(
                user_id=user_id,
                family_member_name=family_member_name,
                voice_id=voice_id,
            )
            db.add(family_voice)

        db.commit()

        return {"message": "Family voice registered."}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.patch("/family/enabled")
def set_family_voice_enabled(
    payload: FamilyVoiceEnabledRequest,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    user = require_user_access(db, payload.user_id, x_device_key)

    if payload.enabled:
        family_voice = db.query(FamilyVoice).filter(FamilyVoice.user_id == payload.user_id).first()
        if not family_voice:
            raise HTTPException(status_code=400, detail="No family voice is registered.")

    user.family_voice_enabled = payload.enabled

    db.commit()
    db.refresh(user)

    return {"family_voice_enabled": user.family_voice_enabled}
