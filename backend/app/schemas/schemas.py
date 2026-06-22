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
