# 추가
import os
import shutil
import tempfile
from fastapi import (
    APIRouter,
    Depends,
    Response,
    Form,
    File,
    UploadFile,
    HTTPException
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import FamilyVoice
from app.routers.users import get_user_or_404
from app.schemas.schemas import TTSRequest
from backend.app.services.tts_service import tts_service
from app.schemas.schemas import FamilyVoiceEnabledRequest

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



@router.post("/family/upload")
async def upload_family_voice(
    user_id: int = Form(...),
    family_member_name: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)

    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="음성 파일이 없습니다.",
        )

    ext = os.path.splitext(audio.filename)[1].lower()

    if ext not in [".wav", ".mp3", ".m4a"]:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다.",
        )

    #
    # 추가: 임시 저장
    #
    with tempfile.NamedTemporaryFile(
        suffix=ext,
        delete=False,
    ) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    try:
        #
        # XTTS용 음성 등록
        #
        voice_model_id = (
            tts_service.register_family_voice(
                user_id,
                tmp_path
            )
        )

        family_voice = (
            db.query(FamilyVoice)
            .filter(FamilyVoice.user_id == user_id)
            .first()
        )

        if family_voice:
            # 변경
            family_voice.family_member_name = (
                family_member_name
            )
            family_voice.voice_model_id = (
                voice_model_id
            )
            family_voice.voice_sample_path = (
                voice_model_id
            )
        else:
            # 변경
            family_voice = FamilyVoice(
                user_id=user_id,
                family_member_name=family_member_name,
                voice_model_id=voice_model_id,
                voice_sample_path=voice_model_id,
            )
            db.add(family_voice)

        db.commit()

        return {
            "message": "가족 음성이 등록되었습니다."
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.patch("/family/enabled")
async def set_family_voice_enabled(
    payload: FamilyVoiceEnabledRequest,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(
        db,
        payload.user_id,
    )

    if payload.enabled:
        family_voice = (
            db.query(FamilyVoice)
            .filter(
                FamilyVoice.user_id == payload.user_id
            )
            .first()
        )

        if not family_voice:
            raise HTTPException(
                status_code=400,
                detail="등록된 가족 음성이 없습니다.",
            )

    user.family_voice_enabled = payload.enabled

    db.commit()

    return {
        "family_voice_enabled":
            user.family_voice_enabled
    }
