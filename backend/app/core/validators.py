import re
from typing import Optional, List
from pydantic import BaseModel, field_validator
from fastapi import HTTPException, status
from pathlib import Path
from app.core.logging_config import logger


class TextInputValidator(BaseModel):
    """Validator for text inputs to prevent injection attacks."""
    text: str
    max_length: int = 10000
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        
        if len(v) > cls.max_length:
            raise ValueError(f"Text exceeds maximum length of {cls.max_length}")
        
        # Check for potential injection patterns
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Text contains potentially dangerous content")
        
        return v.strip()


class QueryValidator(BaseModel):
    """Validator for query inputs."""
    query: str
    max_length: int = 500
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        
        if len(v) > cls.max_length:
            raise ValueError(f"Query exceeds maximum length of {cls.max_length}")
        
        return v.strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized


def validate_audio_file(filename: str) -> bool:
    """Validate audio file extension."""
    allowed_extensions = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}
    return Path(filename).suffix.lower() in allowed_extensions


def validate_username(username: str) -> bool:
    """Validate username format."""
    if not username or not isinstance(username, str):
        raise HTTPException(status_code=400, detail="Username is required")
    
    if len(username) < 3 or len(username) > 50:
        raise HTTPException(status_code=400, detail="Username must be between 3 and 50 characters")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, underscores, and hyphens")
    
    return True


def validate_password(password: str) -> bool:
    """Validate password strength."""
    if not password or not isinstance(password, str):
        raise HTTPException(status_code=400, detail="Password is required")
    
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Check for at least one letter and one number
    if not re.search(r'[A-Za-z]', password):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter")
    
    if not re.search(r'[0-9]', password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    return True


def validate_session_type(session_type: str) -> bool:
    """Validate session type."""
    valid_types = ["manual", "lecture", "meeting", "general", "short"]
    
    if not session_type or session_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid session_type. Must be one of: {valid_types}")
    
    return True


def validate_duration(duration: int) -> bool:
    """Validate recording duration."""
    if not isinstance(duration, int):
        raise HTTPException(status_code=400, detail="Duration must be an integer")
    
    if duration < 1 or duration > 3600:  # Max 1 hour
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 3600 seconds")
    
    return True


def validate_task_id(task_id: str) -> bool:
    """Validate task ID format."""
    if not task_id or not isinstance(task_id, str):
        raise HTTPException(status_code=400, detail="Task ID is required")
    
    if len(task_id) < 5 or len(task_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    return True


def validate_limit(limit: int, default: int = 10, max_limit: int = 100) -> int:
    """Validate and sanitize limit parameter."""
    if not isinstance(limit, int):
        return default
    
    if limit < 1:
        return 1
    
    if limit > max_limit:
        return max_limit
    
    return limit


def validate_memory_id(memory_id: str) -> bool:
    """Validate memory ID format."""
    if not memory_id or not isinstance(memory_id, str):
        raise HTTPException(status_code=400, detail="Memory ID is required")
    
    if len(memory_id) < 5:
        raise HTTPException(status_code=400, detail="Invalid memory ID format")
    
    return True


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize string input by removing potentially harmful characters."""
    if not text:
        return ""
    
    # Remove null bytes and control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def validate_importance_threshold(threshold: float) -> bool:
    """Validate importance threshold."""
    if not isinstance(threshold, (int, float)):
        raise HTTPException(status_code=400, detail="Importance threshold must be a number")
    
    if threshold < 0.0 or threshold > 1.0:
        raise HTTPException(status_code=400, detail="Importance threshold must be between 0.0 and 1.0")
    
    return True
