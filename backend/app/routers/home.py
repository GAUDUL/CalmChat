from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Conversation

router = APIRouter(prefix="/home", tags=["home"])

@router.get("/recent-messages")
def get_recent_messages(user_id: int, db: Session = Depends(get_db)):

    messages = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
        .all()
    )

    return [
        {
            "id": m.id,
            "content": m.content,
            "role": m.role,
            "created_at": m.created_at,
        }
        for m in messages
    ]