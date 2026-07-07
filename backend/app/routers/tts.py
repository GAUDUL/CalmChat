import os
import shutil
import tempfile
import requests

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

    reference_audio_path = None

    if payload.use_family_voice:
        family_voice = (
            db.query(FamilyVoice)
            .filter(FamilyVoice.user_id == payload.user_id)
            .first()
        )

        if family_voice:
            reference_audio_path = family_voice.sample_audio_path

    audio_bytes = tts_service.synthesize(
        text=payload.text,
        reference_audio_path=reference_audio_path,
        use_family_voice=bool(reference_audio_path),
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
        sample_audio_path, embedding_path = tts_service.register_family_voice(tmp_path)

        family_voice = db.query(FamilyVoice).filter(FamilyVoice.user_id == user_id).first()

        # 이미 있으면 수정
        if family_voice:
            family_voice.family_member_name = family_member_name
            family_voice.sample_audio_path = sample_audio_path
            family_voice.embedding_path = embedding_path
        # 없었으면 생성
        else:
            family_voice = FamilyVoice(
                user_id=user_id,
                family_member_name=family_member_name,
                sample_audio_path=sample_audio_path,
                embedding_path=embedding_path,
            )
            db.add(family_voice)

        db.commit()

        return {"message": "Family voice registered."}
    except requests.HTTPError:
        raise HTTPException(status_code=422, detail="음성 임베딩 추출에 실패했습니다. 다른 샘플로 시도해 주세요.")
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
