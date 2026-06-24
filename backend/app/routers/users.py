from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.schemas.schemas import DeviceUserRequest, UserPreferenceUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def clean_optional_text(value: str | None) -> str | None:
    # Store blank optional form fields as NULL so "missing profile data" checks stay simple.
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.family_voice_enabled is None:
        user.family_voice_enabled = False
    return user


@router.post("/device", response_model=UserResponse)
async def register_device_user(payload: DeviceUserRequest, db: Session = Depends(get_db)):
    # First launch / returning launch entrypoint: reuse the same user row for this device.
    user = db.query(User).filter(User.device_key == payload.device_key).first()
    if user:
        if user.family_voice_enabled is None:
            user.family_voice_enabled = False
        return user

    user = User(device_key=payload.device_key, name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_user_or_404(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserPreferenceUpdate,
    db: Session = Depends(get_db),
):
    # Onboarding and profile settings both update the same users row.
    user = get_user_or_404(db, user_id)

    if payload.name is not None:
        name = clean_optional_text(payload.name)
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        user.name = name

    if payload.phone is not None:
        phone = clean_optional_text(payload.phone)
        if phone:
            # Phone is optional, but if provided it must still identify only one user.
            existing_phone_user = (
                db.query(User)
                .filter(User.phone == phone, User.id != user.id)
                .first()
            )
            if existing_phone_user:
                raise HTTPException(status_code=409, detail="Phone already registered")
        user.phone = phone

    if payload.region_dialect is not None:
        user.region_dialect = clean_optional_text(payload.region_dialect)

    if payload.family_voice_enabled is not None:
        user.family_voice_enabled = payload.family_voice_enabled

    db.commit()
    db.refresh(user)
    return user
