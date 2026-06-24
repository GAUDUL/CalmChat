from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class STTResponse(BaseModel):
    text: str
    confidence: Optional[float] = None


class ChatRequest(BaseModel):
    user_id: int
    text: str


class ChatResponse(BaseModel):
    response_text: str
    used_context: Optional[List[str]] = None


class VoiceChatResponse(ChatResponse):
    text: str
    confidence: Optional[float] = None


class DeviceUserRequest(BaseModel):
    device_key: str
    name: str = "CalmChat User"


class UserResponse(BaseModel):
    id: int
    name: str
    device_key: Optional[str] = None
    phone: Optional[str] = None
    region_dialect: Optional[str] = None
    family_voice_enabled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserPreferenceUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    region_dialect: Optional[str] = None
    family_voice_enabled: Optional[bool] = None


class TTSRequest(BaseModel):
    text: str
    user_id: int
    use_family_voice: bool = False


class ProfileUpdateRequest(BaseModel):
    user_id: int


class ProfileUpdateResponse(BaseModel):
    status: str
    updated_at: datetime


class MetricsResponse(BaseModel):
    user_id: int
    emotion_score: Optional[float] = None
    energy_score: Optional[float] = None
    anomaly_detected: bool
    recommended_solution: Optional[str] = None


class FamilyVoiceRegisterRequest(BaseModel):
    user_id: int
    family_member_name: str
