from typing import List, Optional, Dict, Any
import time

from pydantic import BaseModel, Field


class Memory(BaseModel):
    text: str
    timestamp: float = Field(default_factory=time.time)
    speaker: str = "unknown"
    importance: float = 0.5
    tags: List[str] = Field(default_factory=list)
    source: str = "audio"
    audio_file: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryQuery(BaseModel):
    query: str
    limit: int = 5
    speaker_filter: Optional[str] = None
    importance_threshold: float = 0.0

class MemoryResponse(BaseModel):
    memories: List[Memory]
    total: int
    query_time: float
