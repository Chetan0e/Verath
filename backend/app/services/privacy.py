from app.core.logging_config import logger

# In-memory cache layer — fast path for repeated checks within a process lifetime.
# Populated lazily from MongoDB on cache miss. Invalidated on toggle.
_PRIVATE_MODES: dict[str, bool] = {}


async def toggle_privacy(user_id: str) -> bool:
    """Toggle privacy mode for a user and persist state to MongoDB."""
    from app.services.database import get_db
    db = get_db()

    # Read current state from MongoDB (source of truth)
    user_doc = await db["users"].find_one(
        {"username": user_id},
        {"privacy_enabled": 1}
    )
    current_state = user_doc.get("privacy_enabled", False) if user_doc else False
    new_state = not current_state

    # Persist to MongoDB
    await db["users"].update_one(
        {"username": user_id},
        {"$set": {"privacy_enabled": new_state}},
        upsert=True
    )

    # Update in-memory cache
    _PRIVATE_MODES[user_id] = new_state
    logger.info(f"Privacy mode for user {user_id} set to {new_state}")
    return new_state


async def is_private(user_id: str) -> bool:
    """
    Check if privacy mode is enabled for a user.
    Uses in-memory cache with MongoDB fallback to survive server restarts.
    """
    # Cache hit — fast path
    if user_id in _PRIVATE_MODES:
        return _PRIVATE_MODES[user_id]

    # Cache miss — query MongoDB (e.g. after server restart)
    from app.services.database import get_db
    db = get_db()

    user_doc = await db["users"].find_one(
        {"username": user_id},
        {"privacy_enabled": 1}
    )
    state = user_doc.get("privacy_enabled", False) if user_doc else False

    # Populate cache
    _PRIVATE_MODES[user_id] = state
    return state