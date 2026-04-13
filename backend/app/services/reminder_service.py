import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger(__name__)

_mongo = AsyncIOMotorClient(settings.mongo_uri)
_db = _mongo[settings.database_name]
_memories_col = _db["memories"]
_alerts_col = _db["alerts"]

# Intents that carry a meaningful date we should alert on
ALERTABLE_INTENTS = {"meeting", "deadline", "reminder", "commitment"}

# How far ahead to look
LOOKAHEAD_HOURS = 24


async def check_and_fire_reminders() -> int:
    """
    Called by the scheduler every 15 minutes.
    Scans memories with upcoming parsed dates and creates alert records
    for any that haven't been alerted yet.
    Returns the number of new alerts created.
    """
    now = datetime.utcnow()
    window_end = now + timedelta(hours=LOOKAHEAD_HOURS)

    # Find memories with a parsed date inside the lookahead window
    cursor = _memories_col.find({
        "metadata.intent": {"$in": list(ALERTABLE_INTENTS)},
        "metadata.entities.dates": {"$exists": True, "$ne": []},
    })

    new_alert_count = 0

    async for memory in cursor:
        entities = memory.get("metadata", {}).get("entities", {})
        dates = entities.get("dates", [])

        for date_entry in dates:
            # Handle both string dates and dict objects with parsed_date field
            if isinstance(date_entry, str):
                parsed_str = date_entry
            elif isinstance(date_entry, dict):
                parsed_str = date_entry.get("parsed_date") or date_entry.get("phrase")
            else:
                continue

            if not parsed_str:
                continue

            try:
                # Try to parse as ISO format first
                if isinstance(parsed_str, str):
                    parsed_date = datetime.fromisoformat(parsed_str)
                else:
                    continue
            except (ValueError, TypeError):
                # Try using dateparser as fallback
                try:
                    import dateparser
                    parsed_date = dateparser.parse(parsed_str, settings={
                        'RELATIVE_BASE': now,
                        'PREFER_DATES_FROM': 'future'
                    })
                    if not parsed_date:
                        continue
                except:
                    continue

            # Only alert if the event is within the lookahead window
            if not (now <= parsed_date <= window_end):
                continue

            memory_id = str(memory["_id"])
            user_id = memory.get("user_id", "unknown")

            # Deduplication: skip if we already alerted for this memory + date
            existing = await _alerts_col.find_one({
                "memory_id": memory_id,
                "parsed_date": parsed_str,
            })
            if existing:
                continue

            # Create alert record
            alert = {
                "memory_id": memory_id,
                "user_id": user_id,
                "text": memory.get("text", ""),
                "intent": memory.get("metadata", {}).get("intent", "reminder"),
                "parsed_date": parsed_str,
                "due_in_minutes": int((parsed_date - now).total_seconds() / 60),
                "alerted_at": now,
                "acknowledged": False,
            }
            await _alerts_col.insert_one(alert)
            new_alert_count += 1

            logger.info(
                f"[Reminder] user={user_id} intent={alert['intent']} "
                f"due_in={alert['due_in_minutes']}min text='{alert['text'][:60]}'"
            )

    if new_alert_count:
        logger.info(f"[Reminder] Fired {new_alert_count} new alert(s)")

    return new_alert_count


async def get_upcoming_reminders(
    user_id: str,
    hours: int = 24,
    include_acknowledged: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch pending reminder alerts for a user from the alerts collection.
    Used by the /reminders/upcoming endpoint.
    """
    now = datetime.utcnow()
    window_end = now + timedelta(hours=hours)

    query: Dict[str, Any] = {
        "user_id": user_id,
        "alerted_at": {"$gte": now - timedelta(hours=hours)},
    }
    if not include_acknowledged:
        query["acknowledged"] = False

    reminders = []
    cursor = _alerts_col.find(query).sort("due_in_minutes", 1)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        reminders.append(doc)

    return reminders


async def acknowledge_reminder(alert_id: str, user_id: str) -> bool:
    """Mark a reminder as acknowledged so it won't re-appear."""
    from bson import ObjectId
    result = await _alerts_col.update_one(
        {"_id": ObjectId(alert_id), "user_id": user_id},
        {"$set": {"acknowledged": True}}
    )
    return result.modified_count > 0
