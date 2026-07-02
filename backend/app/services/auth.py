import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.services.database import get_db


logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days in minutes
REFRESH_TOKEN_EXPIRE_DAYS = 30

ALGORITHM = "HS256"


# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ── Token creation ────────────────────────────────────────────────────────────
def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())
    payload = {"sub": username, "type": "access", "exp": expire, "jti": jti}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {"sub": username, "type": "refresh", "exp": expire, "jti": jti}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────────
async def verify_access_token(token: str) -> Optional[str]:
    """Returns username if valid access token, else None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        jti = payload.get("jti")
        if jti:
            db = get_db()
            if db is not None:
                blacklisted = await db["blacklisted_tokens"].find_one({"jti": jti})
                if blacklisted:
                    return None
        return payload.get("sub")
    except JWTError:
        return None


async def verify_refresh_token(token: str) -> Optional[str]:
    """Returns username if valid refresh token, else None.

    Also checks the blacklisted_tokens collection so that rotated (or
    explicitly revoked) refresh tokens cannot be reused.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        jti = payload.get("jti")
        if jti:
            db = get_db()
            if db is not None:
                blacklisted = await db["blacklisted_tokens"].find_one({"jti": jti})
                if blacklisted:
                    return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[Dict]:
    """Decode access token and return payload, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ── User operations ───────────────────────────────────────────────────────────
async def create_user(username: str, password: str) -> bool:
    username = username.lower().strip()
    db = get_db()
    existing = await db["users"].find_one({"username": username})
    if existing:
        return False
    await db["users"].insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    })
    return True


async def authenticate_user(username: str, password: str) -> Optional[str]:
    username = username.lower().strip()
    db = get_db()
    user = await db["users"].find_one({"username": username})
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return username


# ── Account lockout (brute-force protection) ──────────────────────────────────
async def get_lockout_seconds_remaining(username: str) -> int:
    """Return seconds remaining on an active lockout, or 0 if not locked."""
    username = username.lower().strip()
    db = get_db()
    record = await db["login_attempts"].find_one({"username": username})
    if not record:
        return 0
    locked_until = record.get("locked_until")
    if locked_until and locked_until > datetime.utcnow():
        return int((locked_until - datetime.utcnow()).total_seconds())
    return 0


async def register_failed_login(username: str) -> None:
    """Record a failed attempt; lock the account once the threshold is hit."""
    username = username.lower().strip()
    now = datetime.utcnow()
    db = get_db()
    record = await db["login_attempts"].find_one({"username": username})
    failures = (record.get("failures", 0) if record else 0) + 1

    update = {"failures": failures, "last_failed_at": now}
    if failures >= settings.login_max_failures:
        update["locked_until"] = now + timedelta(minutes=settings.login_lockout_minutes)
        logger.warning(
            f"AUTH LOCKOUT: account locked - username={username} "
            f"failures={failures} minutes={settings.login_lockout_minutes}"
        )

    await db["login_attempts"].update_one(
        {"username": username},
        {"$set": update},
        upsert=True,
    )


async def reset_login_attempts(username: str) -> None:
    """Clear any failure record on successful authentication."""
    username = username.lower().strip()
    db = get_db()
    await db["login_attempts"].delete_one({"username": username})


async def get_user_id_from_username(username: str) -> Optional[str]:
    """Get user_id from username."""
    username = username.lower().strip()
    db = get_db()
    user = await db["users"].find_one({"username": username})
    if not user:
        return None
    return str(user.get("_id")) if "_id" in user else username


# ── FastAPI dependencies ──────────────────────────────────────────────────────
_bearer = HTTPBearer()


async def get_current_user_id(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Extract and verify user ID from Bearer token."""
    username = await verify_access_token(creds.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, str]:
    """
    Backward-compatible auth dependency wrapper.

    Returns user context dict expected by older route handlers.
    """
    username = await verify_access_token(creds.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {"username": username}