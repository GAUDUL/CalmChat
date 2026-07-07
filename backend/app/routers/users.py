from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User
from app.schemas.schemas import DeviceUserRequest, UserPreferenceUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changed = False
    if user.family_voice_enabled is None:
        user.family_voice_enabled = False
        changed = True
    if user.onboarding_completed is None:
        user.onboarding_completed = bool(user.name and user.phone and user.region_dialect)
        changed = True
    # Persist legacy NULL values once when they are observed.
    if changed:
        db.commit()
        db.refresh(user)
    return user


def require_user_access(
    db: Session,
    user_id: int,
    x_device_key: str | None,
) -> User:
    user = get_user_or_404(db, user_id)
    # This is not full account auth, but it closes the IDOR hole in the current
    # device-key identity model by binding requests to the device-created user.
    if not x_device_key or user.device_key != x_device_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.post("/device", response_model=UserResponse)
def register_device_user(payload: DeviceUserRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.device_key == payload.device_key).first()
    if user:
        return get_user_or_404(db, user.id)

    user = User(device_key=payload.device_key, name=payload.name, onboarding_completed=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    return require_user_access(db, user_id, x_device_key)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserPreferenceUpdate,
    db: Session = Depends(get_db),
    x_device_key: str | None = Header(default=None),
):
    user = require_user_access(db, user_id, x_device_key)

    if payload.name is not None:
        name = clean_optional_text(payload.name)
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        user.name = name

    if payload.phone is not None:
        phone = clean_optional_text(payload.phone)
        if phone:
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

    user.onboarding_completed = bool(user.name and user.phone and user.region_dialect)

    db.commit()
    db.refresh(user)
    return user
