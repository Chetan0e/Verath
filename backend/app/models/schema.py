from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import DEFAULT_RECORD_SECONDS
from app.models.memory import Memory


class RecordRequest(BaseModel):
    duration: int = Field(default=DEFAULT_RECORD_SECONDS, ge=1, le=120)
    filename: str = "temp.wav"


class QueryResponse(BaseModel):
    answer: str
    context: List[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    summary: str


class TimelineItem(Memory):
    id: Optional[int] = None


class VoiceTrainRequest(BaseModel):
    name: str
    sample_text: Optional[str] = None


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
