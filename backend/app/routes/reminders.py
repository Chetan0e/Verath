import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.services.reminder_service import (
    get_upcoming_reminders,
    acknowledge_reminder,
)
from app.services.auth import verify_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reminders", tags=["reminders"])
_bearer = HTTPBearer()


# ── Auth helper ───────────────────────────────────────────────────────────────
async def _get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    username = verify_access_token(creds.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


# ── Schemas ───────────────────────────────────────────────────────────────────
class ReminderItem(BaseModel):
    id: str
    memory_id: str
    user_id: str
    text: str
    intent: str
    parsed_date: str
    due_in_minutes: int
    alerted_at: str
    acknowledged: bool


class UpcomingRemindersResponse(BaseModel):
    count: int
    reminders: List[dict]


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/upcoming", response_model=UpcomingRemindersResponse)
async def get_upcoming(
    hours: int = Query(default=24, ge=1, le=168, description="Lookahead window in hours"),
    include_acknowledged: bool = Query(default=False),
    user: str = Depends(_get_current_user),
):
    """
    Return all pending reminder alerts for the current user
    within the next `hours` hours (default 24).
    """
    if not (1 <= hours <= 168):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "message": "hours must be between 1 and 168",
                "field": "hours",
                "received": hours
            }
        )
    reminders = await get_upcoming_reminders(
        user_id=user,
        hours=hours,
        include_acknowledged=include_acknowledged,
    )
    return UpcomingRemindersResponse(count=len(reminders), reminders=reminders)


@router.post("/{alert_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge(
    alert_id: str,
    user: str = Depends(_get_current_user),
):
    """Mark a reminder alert as acknowledged so it is hidden from future queries."""
    success = await acknowledge_reminder(alert_id=alert_id, user_id=user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or already acknowledged",
        )
    return {"message": "Reminder acknowledged", "alert_id": alert_id}
