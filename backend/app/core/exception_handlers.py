from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import VerathException, http_exception_from_error
from app.core.logging_config import logger

def build_error_response(request: Request, status_code: int, error_type: str, message: str, details: dict = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "message": message,
            "path": request.url.path,
            "details": details or {}
        }
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="Internal Server Error",
        message="An unexpected error occurred. Please try again later."
    )

async def verath_exception_handler(request: Request, exc: VerathException) -> JSONResponse:
    """Handler for domain-specific Verath exceptions."""
    http_exc = http_exception_from_error(exc)
    
    logger.warning(f"VerathException at {request.url.path}: {exc.message}")
    return build_error_response(
        request=request,
        status_code=http_exc.status_code,
        error_type=type(exc).__name__,
        message=exc.message,
        details=exc.details
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
        
    return build_error_response(
        request=request,
        status_code=exc.status_code,
        error_type=error_type,
        message=message,
        details=details
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized handler for validation errors."""
    logger.warning(f"Validation error at {request.url.path}: {exc.errors()}")
    return build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_type="ValidationError",
        message="The request data is invalid.",
        details={"errors": exc.errors()}
    )
