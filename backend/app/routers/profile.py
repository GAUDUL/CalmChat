from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Conversation, ProfileDocument
from app.schemas.schemas import ProfileUpdateRequest, ProfileUpdateResponse
from app.services.rag_service import rag_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/update", response_model=ProfileUpdateResponse)
async def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db)):
    """프론트: 대화 종료 -> POST /profile/update -> 프로파일 DB 갱신 -> 상태 코드 반환"""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == payload.user_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )
    texts = [f"{c.role}: {c.content}" for c in conversations]

    summary = rag_service.regenerate_profile_from_history(payload.user_id, texts)

    profile = db.query(ProfileDocument).filter(ProfileDocument.user_id == payload.user_id).first()
    if profile:
        profile.content = summary
    else:
        profile = ProfileDocument(user_id=payload.user_id, content=summary)
        db.add(profile)
    db.commit()

    return ProfileUpdateResponse(status="ok", updated_at=datetime.utcnow())
