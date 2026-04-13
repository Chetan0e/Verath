import re
from typing import Any, Dict
from fastapi import Request, HTTPException, status


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string input by removing potentially harmful characters.
    - Strip HTML tags
    - Remove null bytes and control characters (except newlines and tabs)
    - Truncate to max_length
    """
    if not value:
        return ""
    
    # Strip HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    
    # Remove null bytes and control characters except newlines, tabs, carriage returns
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    
    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()


def sanitize_dict(data: Dict[str, Any], max_length: int = 10000) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value, max_length)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_length)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_string(v, max_length) if isinstance(v, str) else v for v in value]
        else:
            sanitized[key] = value
    return sanitized


class SanitizationMiddleware:
    """FastAPI middleware to sanitize all request bodies."""
    
    async def __call__(self, request: Request, call_next):
        # Only sanitize POST, PUT, PATCH requests with JSON bodies
        if request.method in ("POST", "PUT", "PATCH") and "application/json" in request.headers.get("content-type", ""):
            body = await request.body()
            if body:
                try:
                    import json
                    data = json.loads(body.decode())
                    if isinstance(data, dict):
                        sanitized_data = sanitize_dict(data)
                        # Replace the request body with sanitized data
                        request._body = json.dumps(sanitized_data).encode()
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # If body is not valid JSON, leave it as is
                    pass
        
        response = await call_next(request)
        return response
