import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.database import get_db
from app.services.summarizer import generate_period_summary

logger = logging.getLogger(__name__)

# Default digest window: one week
DEFAULT_WINDOW_HOURS = 168


async def _get_active_user_ids(window_hours: int) -> List[str]:
    """Return user_ids with memory activity in the window.

    Filters on `created_at`, the BSON Date field used by the other memory
    queries in the codebase (get_memory_stats, all_memories_filtered). The
    `timestamp` field is stored as an ISO string, so a datetime `$gte`
    predicate against it never matches in MongoDB.
    """
    db = get_db()
    if db is None:
        return []
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    user_ids = await db["memories"].distinct(
        "user_id", {"created_at": {"$gte": cutoff}}
    )
    return [str(uid) for uid in user_ids if uid]


async def generate_and_store_digest(
    user_id: str, window_hours: int = DEFAULT_WINDOW_HOURS
) -> Dict[str, Any]:
    """Generate a period summary for one user and persist it to the digests collection."""
    summary = await generate_period_summary(user_id, hours=window_hours)
    doc = {
        "user_id": user_id,
        "generated_at": datetime.utcnow(),
        "window_hours": window_hours,
        "summary": summary,
    }
    await get_db()["digests"].insert_one(doc)
    logger.info(f"Stored digest for user {user_id} (window {window_hours}h)")
    return doc


async def get_latest_digest(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recently generated digest for a user, or None."""
    return await get_db()["digests"].find_one(
        {"user_id": user_id}, sort=[("generated_at", -1)]
    )


async def run_weekly_digests(window_hours: int = DEFAULT_WINDOW_HOURS) -> int:
    """Scheduler job: generate and store a digest for each active user.

    Only users with memory activity in the window are processed, so inactive
    users do not trigger empty digests. Returns the number of digests created.
    """
    count = 0
    active_user_ids = await _get_active_user_ids(window_hours)
    for user_id in active_user_ids:
        try:
            await generate_and_store_digest(user_id, window_hours=window_hours)
            count += 1
        except Exception as e:
            logger.error(
                f"Failed to generate digest for user {user_id}: {e}",
                exc_info=True,
            )
    logger.info(f"Weekly digest job complete: {count} digests generated")
    return count