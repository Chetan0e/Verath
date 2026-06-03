from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCredentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Memory ────────────────────────────────────────────────────────────────────
class MemoryCreate(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = {}


class MemoryResponse(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    lifecycle: str
    created_at: str


# ── Query ─────────────────────────────────────────────────────────────────────
class SourceInfo(BaseModel):
    speaker: str = "unknown"
    intent: str = "general"
    timestamp: str = ""
    importance: float = 0.0
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Cross-encoder confidence for this specific source (0–1)",
    )


class QueryResponse(BaseModel):
    answer: str
    context: List[str]
    sources: List[SourceInfo]
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Overall answer confidence based on the top re-ranked source. "
            "0.0 = very uncertain, 1.0 = highly confident."
        ),
    )
    confidence: float | None = None


# ── Pipeline ──────────────────────────────────────────────────────────────────
class ExtractRequest(BaseModel):
    text: str


class ValidateRequest(BaseModel):
    text: str


class SessionRecordRequest(BaseModel):
    session_type: str = "general"
    duration: int = 10
    filename: Optional[str] = None


# ── Recording ─────────────────────────────────────────────────────────────────
class RecordRequest(BaseModel):
    duration: int = 10
    filename: Optional[str] = None


# ── Stats ─────────────────────────────────────────────────────────────────────
class StatsResponse(BaseModel):
    total: int
    by_intent: Dict[str, int]
    by_speaker: Dict[str, int]
    avg_importance: float
    recent_count: int


# ── Speaker ───────────────────────────────────────────────────────────────────
class VoiceTrainRequest(BaseModel):
    name: str
    sample_text: Optional[str] = None
