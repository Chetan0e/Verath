from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import VerathException
from app.core.logging_config import logger

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": request.url.path,
            "details": {}
        }
    )

async def verath_exception_handler(request: Request, exc: VerathException) -> JSONResponse:
    """Handler for domain-specific Verath exceptions."""
    from app.core.exceptions import http_exception_from_error
    http_exc = http_exception_from_error(exc)
    
    logger.warning(f"VerathException at {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "path": request.url.path,
            "details": exc.details
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Override default HTTPException handler for standardized responses."""
    logger.warning(f"HTTPException at {request.url.path}: status {exc.status_code} - {exc.detail}")
    
    # Sometimes detail is a dict, sometimes a string
    error_type = "HTTPException"
    message = str(exc.detail)
    details = {}
    
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", message)
        error_type = exc.detail.get("type", error_type)
        details = exc.detail.get("details", {})
    elif exc.status_code == 404:
        error_type = "NotFoundError"
    elif exc.status_code == 401:
        error_type = "AuthenticationError"
    elif exc.status_code == 403:
        error_type = "AuthorizationError"
        
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_type,
            "message": message,
            "path": request.url.path,
            "details": details
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized handler for validation errors."""
    logger.warning(f"Validation error at {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "The request data is invalid.",
            "path": request.url.path,
            "details": {"errors": exc.errors()}
        }
    )
