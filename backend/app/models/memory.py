from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal, Annotated
from datetime import datetime
from bson import ObjectId
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        python_schema = core_schema.with_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                str,
                return_schema=core_schema.str_schema(),
            ),
        )
        return python_schema

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler):
        return {"type": "string"}


class Memory(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    text: str
    cleaned_text: Optional[str] = None
    intent: Optional[str] = None
    entities: Dict = Field(default_factory=dict)
    summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speaker: str = "unknown"
    importance: float = 0.5
    tags: List[str] = Field(default_factory=list)
    source: str = "audio"
    audio_file: Optional[str] = None
    embedding: List[float] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    user_id: str
    has_correction: bool = False
    importance_boost: float = 0.0
    session_type: Optional[Literal["manual", "lecture", "meeting", "general", "short"]] = "general"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    lifecycle_stage: Literal["short_term", "long_term", "archived"] = "short_term"
    is_duplicate: bool = False
    duplicate_of: Optional[PyObjectId] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class MemoryQuery(BaseModel):
    query: str
    limit: int = 5
    intent_filter: Optional[str] = None
    speaker_filter: Optional[str] = None
    importance_threshold: float = 0.0
    date_filter: Optional[datetime] = None
    session_type_filter: Optional[str] = None


class MemoryResponse(BaseModel):
    answer: str
    context: List[str]
    sources: List[Dict[str, Any]]


class TimelineItem(BaseModel):
    time: str
    text: str
    speaker: str
    importance: float
    tags: List[str]
    intent: Optional[str] = None
    id: str
    session_type: Optional[str] = None


class RecordingSession(BaseModel):
    session_type: Literal["manual", "lecture", "meeting", "general", "short"]
    duration: int = 10
    filename: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
