import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime

from jose import jwt, JWTError

from app.services.auth import (
    authenticate_user,
    create_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    decode_access_token,
    get_current_user,
    ALGORITHM,
    get_lockout_seconds_remaining,
    register_failed_login,
    reset_login_attempts,
)
from app.config import settings
from app.services.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer()

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)


# ── Schemas ───────────────────────────────────────────────────────────────────
class UserCredentials(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    username: str
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
    ip_address = request.client.host if request.client else "unknown"

    # Account lockout check (per-account, complements IP rate limiting)
    lock_seconds = await get_lockout_seconds_remaining(username_clean)
    if lock_seconds > 0:
        await _log_auth_event(username_clean, ip_address, "login_locked", False)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked. Try again in {lock_seconds} seconds.",
            headers={"Retry-After": str(lock_seconds)},
        )

    username = await authenticate_user(username_clean, credentials.password)

    # Audit log
    await _log_auth_event(username_clean, ip_address, "login", username is not None)

    if not username:
        await register_failed_login(username_clean)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await reset_login_attempts(username_clean)

    return TokenResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),
        username=username,
    )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Refresh token rotation: old refresh token is invalidated on use.
    """
    username = await verify_refresh_token(body.refresh_token)
    ip_address = request.client.host if request.client else "unknown"
    
    if not username:
        await _log_auth_event("unknown", ip_address, "refresh", False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Blacklist the consumed refresh token before issuing a new pair.
    # This enforces true rotation: a stolen or replayed token is rejected.
    try:
        old_payload = jwt.decode(
            body.refresh_token, settings.secret_key, algorithms=[ALGORITHM]
        )
        old_jti = old_payload.get("jti")
        old_exp = old_payload.get("exp")
        if old_jti and old_exp:
            db = get_db()
            if db is not None:
                await db["blacklisted_tokens"].insert_one({
                    "jti": old_jti,
                    "exp": datetime.fromtimestamp(old_exp),
                    "blacklisted_at": datetime.utcnow(),
                    "username": username,
                    "reason": "refresh_rotation",
                })
    except (JWTError, Exception):
        pass  # Token was already validated above; decoding won't fail here
    
    await _log_auth_event(username, ip_address, "refresh", True)
    
    return TokenResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),  # rotate
        username=username,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    Logout user and invalidate their access token.
    Stores the JWT ID (jti) in the blacklist collection.

    Auth goes through get_current_user, which calls verify_access_token and
    rejects already-blacklisted tokens (401) — consistent with every other
    protected route, so a blacklisted token never reaches the insert below.
    The DuplicateKeyError guard remains as defense-in-depth so a race or
    repeat never surfaces as an unhandled 500.
    """
    payload = decode_access_token(creds.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    jti = payload.get("jti")
    exp = payload.get("exp")
    username = current_user["username"]
    ip_address = request.client.host if request.client else "unknown"

    if jti and exp:
        db = get_db()
        try:
            await db["blacklisted_tokens"].insert_one({
                "jti": jti,
                "exp": datetime.fromtimestamp(exp),
                "blacklisted_at": datetime.utcnow(),
                "username": username,
            })
        except DuplicateKeyError:
            # Already blacklisted — treat repeat logout as success (idempotent).
            pass

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