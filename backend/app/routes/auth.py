import logging
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime

from app.services.auth import (
    authenticate_user,
    create_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    decode_access_token,
)
from app.services.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)
router.state.limiter = limiter
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Schemas ───────────────────────────────────────────────────────────────────
class UserCredentials(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/signup", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(request: Request, credentials: UserCredentials):
    username = credentials.username.lower().strip()
    ip_address = request.client.host if request.client else "unknown"
    
    success = await create_user(username, credentials.password)
    
    # Audit log
    await _log_auth_event(username, ip_address, "signup", success)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    return {"message": "User created successfully", "username": username}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserCredentials):
    username_clean = credentials.username.lower().strip()
    username = await authenticate_user(username_clean, credentials.password)
    ip_address = request.client.host if request.client else "unknown"
    
    # Audit log
    await _log_auth_event(username_clean, ip_address, "login", username is not None)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Refresh token rotation: old refresh token is invalidated on use.
    """
    username = verify_refresh_token(body.refresh_token)
    ip_address = request.client.host if request.client else "unknown"
    
    if not username:
        await _log_auth_event("unknown", ip_address, "refresh", False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    await _log_auth_event(username, ip_address, "refresh", True)
    
    return TokenResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),  # rotate
    )


@router.post("/logout")
async def logout(request: Request):
    """
    Logout user and invalidate their access token.
    Stores the JWT ID (jti) in the blacklist collection.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authorization token provided"
        )
    
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    jti = payload.get("jti")
    exp = payload.get("exp")
    username = payload.get("sub")
    ip_address = request.client.host if request.client else "unknown"
    
    if jti and exp:
        # Add to blacklist
        db = get_db()
        await db["blacklisted_tokens"].insert_one({
            "jti": jti,
            "exp": datetime.fromtimestamp(exp),
            "blacklisted_at": datetime.utcnow(),
            "username": username
        })
    
    await _log_auth_event(username, ip_address, "logout", True)
    
    return {"message": "Logged out successfully"}


async def _log_auth_event(username: str, ip_address: str, event_type: str, success: bool):
    """Log authentication events to both file and MongoDB."""
    log_entry = {
        "username": username,
        "ip_address": ip_address,
        "event_type": event_type,
        "success": success,
        "timestamp": datetime.utcnow()
    }
    
    # Log to file
    if success:
        logger.info(f"AUTH: {event_type.upper()} - username={username} ip={ip_address}")
    else:
        logger.warning(f"AUTH FAILED: {event_type.upper()} - username={username} ip={ip_address}")
    
    # Log to MongoDB for audit trail
    try:
        db = get_db()
        await db["audit_logs"].insert_one(log_entry)
    except Exception as e:
        logger.error(f"Failed to write audit log to MongoDB: {e}")
