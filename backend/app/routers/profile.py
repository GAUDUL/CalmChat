from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Conversation, ProfileDocument
from app.routers.users import get_user_or_404
from app.schemas.schemas import ProfileUpdateRequest, ProfileUpdateResponse
from app.services.rag_service import rag_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/update", response_model=ProfileUpdateResponse)
async def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db)):
    get_user_or_404(db, payload.user_id)

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == payload.user_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )
    texts = [f"{conversation.role}: {conversation.content}" for conversation in conversations]

    summary = rag_service.regenerate_profile_from_history(payload.user_id, texts)

    profile = (
        db.query(ProfileDocument)
        .filter(ProfileDocument.user_id == payload.user_id)
        .first()
    )
    if profile:
        profile.content = summary
    else:
        profile = ProfileDocument(user_id=payload.user_id, content=summary)
        db.add(profile)
    db.commit()

    return ProfileUpdateResponse(status="ok", updated_at=datetime.utcnow())
