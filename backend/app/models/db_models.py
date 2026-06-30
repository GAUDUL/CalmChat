from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    # Device-based identity for the no-login flow. One app install maps to one user row.
    device_key = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    region_dialect = Column(String(50), nullable=True)
    family_voice_enabled = Column(Boolean, default=False)
    # Explicit state avoids relying on the display name "CalmChat User".
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user")
    metrics = relationship("MetricRecord", back_populates="user")
    profile = relationship("ProfileDocument", uselist=False, back_populates="user")
    family_voices = relationship("FamilyVoice", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(10))
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="conversations")


class ProfileDocument(Base):
    """User profile summary used as long-lived chat context."""

    __tablename__ = "profile_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    content = Column(Text)
    vector_id = Column(String(100), nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="profile")


class MetricRecord(Base):
    """Mood, energy, and safety signals extracted from conversations."""

    __tablename__ = "metric_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    emotion_score = Column(Float, nullable=True)
    energy_score = Column(Float, nullable=True)
    sleep_keyword_flag = Column(Boolean, default=False)
    health_keyword_flag = Column(Boolean, default=False)
    # Crisis/self-harm language is a safety signal, not an ordinary mood keyword.
    crisis_keyword_flag = Column(Boolean, default=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="metrics")


class FamilyVoice(Base):
    __tablename__ = "family_voices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    family_member_name = Column(String(50))
    voice_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="family_voices")
