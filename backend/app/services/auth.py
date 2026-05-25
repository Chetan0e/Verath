import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.services.database import get_db

logger = logging.getLogger(__name__)

_mongo = AsyncIOMotorClient(settings.mongo_uri)
_db = _mongo[settings.database_name]
_users_col = _db["users"]

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


def verify_refresh_token(token: str) -> Optional[str]:
    """Returns username if valid refresh token, else None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
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
    existing = await _users_col.find_one({"username": username})
    if existing:
        return False
    await _users_col.insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    })
    return True


async def authenticate_user(username: str, password: str) -> Optional[str]:
    username = username.lower().strip()
    user = await _users_col.find_one({"username": username})
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return username


async def get_user_id_from_username(username: str) -> Optional[str]:
    """Get user_id from username."""
    username = username.lower().strip()
    user = await _users_col.find_one({"username": username})
    if not user:
        return None
    return str(user.get("_id")) if "_id" in user else username


# ── FastAPI dependencies ─────────────────────────────────────────────────────────
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
