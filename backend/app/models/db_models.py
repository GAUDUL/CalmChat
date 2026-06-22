from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    region_dialect = Column(String(50), nullable=True)  # 예: "경상도", "전라도" (STT 사투리 모델 선택용)
    family_voice_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user")
    metrics = relationship("MetricRecord", back_populates="user")
    profile = relationship("ProfileDocument", uselist=False, back_populates="user")
    family_voices = relationship("FamilyVoice", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(10))  # "user" | "assistant"
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="conversations")


class ProfileDocument(Base):
    """LLM이 주기적으로 생성/갱신하는 사용자 요약 문서 (RAG 컨텍스트로 사용)."""
    __tablename__ = "profile_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    content = Column(Text)
    vector_id = Column(String(100), nullable=True)  # 벡터DB 내 id
    last_updated = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="profile")


class MetricRecord(Base):
    """이상치 탐지에 쓰이는 정서/건강 시계열 포인트."""
    __tablename__ = "metric_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    emotion_score = Column(Float, nullable=True)   # -1.0(부정) ~ 1.0(긍정)
    energy_score = Column(Float, nullable=True)    # 음성 톤/속도 등에서 도출
    sleep_keyword_flag = Column(Boolean, default=False)
    health_keyword_flag = Column(Boolean, default=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="metrics")


class FamilyVoice(Base):
    """TTS 가족 목소리 합성 기능에 쓰이는 음성 샘플/클로닝 모델 메타데이터."""
    __tablename__ = "family_voices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    family_member_name = Column(String(50))
    voice_sample_path = Column(String(255))
    voice_model_id = Column(String(100), nullable=True)  # 클로닝 서비스가 발급한 모델 id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="family_voices")
