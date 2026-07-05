import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestReminders:
    """Test reminder functionality."""

    async def test_memory_with_date_and_alertable_intent_creates_reminder_alert(self, monkeypatch):
        """Memory with alertable intent and a date in the lookahead window creates an alert."""
        from datetime import datetime, timedelta

        # Dynamic future date so the 24-hour window check passes
        future_date = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        mock_memories_col = MagicMock()
        mock_memories_col.find = MagicMock(return_value=_async_cursor([
            {
                "_id": "mem_1",
                "user_id": "test_user",
                "text": "Meeting in an hour",
                "metadata": {
                    "intent": "meeting",
                    "entities": {"dates": [future_date]},
                },
            }
        ]))

        mock_alerts_col = MagicMock()
        mock_alerts_col.find_one = AsyncMock(return_value=None)
        mock_alerts_col.insert_one = AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "memories": mock_memories_col,
            "alerts": mock_alerts_col,
        }.get(name, MagicMock()))
        monkeypatch.setattr("app.services.reminder_service.get_db", lambda: mock_db)

        from app.services.reminder_service import check_and_fire_reminders
        count = await check_and_fire_reminders()

        assert count >= 1
        mock_alerts_col.insert_one.assert_called()

    async def test_z_suffixed_date_does_not_crash_comparison(self, monkeypatch):
        """A memory date ending in 'Z' (timezone-aware) must not raise
        'can't compare offset-naive and offset-aware datetimes'."""
        from datetime import datetime, timedelta, timezone

        # Aware future date, serialized with a trailing Z (the crashing case)
        future_z = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_memories_col = MagicMock()
        mock_memories_col.find = MagicMock(return_value=_async_cursor([
            {
                "_id": "mem_z",
                "user_id": "test_user",
                "text": "Meeting soon",
                "metadata": {
                    "intent": "meeting",
                    "entities": {"dates": [future_z]},
                },
            }
        ]))

        mock_alerts_col = MagicMock()
        mock_alerts_col.find_one = AsyncMock(return_value=None)
        mock_alerts_col.insert_one = AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "memories": mock_memories_col,
            "alerts": mock_alerts_col,
        }.get(name, MagicMock()))
        monkeypatch.setattr("app.services.reminder_service.get_db", lambda: mock_db)

        from app.services.reminder_service import check_and_fire_reminders

        # Must not raise; the Z-date is aware and now is aware after the fix.
        count = await check_and_fire_reminders()
        assert count >= 1
        mock_alerts_col.insert_one.assert_called()

    async def test_naive_date_still_processed_without_error(self, monkeypatch):
        """A naive date (no offset, e.g. from the dateparser fallback path)
        is coerced to UTC and still compared without error."""
        from datetime import datetime, timedelta

        # Naive future date (no Z, no offset)
        future_naive = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

        mock_memories_col = MagicMock()
        mock_memories_col.find = MagicMock(return_value=_async_cursor([
            {
                "_id": "mem_naive",
                "user_id": "test_user",
                "text": "Naive meeting",
                "metadata": {
                    "intent": "meeting",
                    "entities": {"dates": [future_naive]},
                },
            }
        ]))

        mock_alerts_col = MagicMock()
        mock_alerts_col.find_one = AsyncMock(return_value=None)
        mock_alerts_col.insert_one = AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "memories": mock_memories_col,
            "alerts": mock_alerts_col,
        }.get(name, MagicMock()))
        monkeypatch.setattr("app.services.reminder_service.get_db", lambda: mock_db)

        from app.services.reminder_service import check_and_fire_reminders

        count = await check_and_fire_reminders()
        assert count >= 1
        mock_alerts_col.insert_one.assert_called()

    async def test_get_upcoming_reminders_returns_correct_reminders_within_time_window(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that GET /reminders/upcoming returns correct reminders within time window."""
        # Mock get_upcoming_reminders
        async def mock_get_upcoming_reminders(user_id, hours, include_acknowledged):
            now = datetime.utcnow()
            return [
                {
                    "_id": "alert_1",
                    "user_id": user_id,
                    "text": "Meeting in 1 hour",
                    "due_in_minutes": 60,
                    "acknowledged": False,
                    "alerted_at": now
                }
            ]
        
        monkeypatch.setattr("app.services.reminder_service.get_upcoming_reminders", mock_get_upcoming_reminders)
        
        response = await client.get(
            "/reminders/upcoming?hours=24",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data

    async def test_acknowledged_reminder_excluded_by_default(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that acknowledged reminder is excluded by default."""
        async def mock_get_upcoming_reminders(user_id, hours, include_acknowledged):
            now = datetime.utcnow()
            if not include_acknowledged:
                return [
                    {
                        "_id": "alert_1",
                        "user_id": user_id,
                        "text": "Pending reminder",
                        "acknowledged": False,
                        "alerted_at": now
                    }
                ]
            return [
                {
                    "_id": "alert_1",
                    "user_id": user_id,
                    "text": "Pending reminder",
                    "acknowledged": False,
                    "alerted_at": now
                },
                {
                    "_id": "alert_2",
                    "user_id": user_id,
                    "text": "Acknowledged reminder",
                    "acknowledged": True,
                    "alerted_at": now
                }
            ]
        
        monkeypatch.setattr("app.services.reminder_service.get_upcoming_reminders", mock_get_upcoming_reminders)
        
        response = await client.get(
            "/reminders/upcoming",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should only return unacknowledged
        reminders = data.get("reminders", [])
        for reminder in reminders:
            assert reminder.get("acknowledged") == False

    async def test_post_acknowledge_sets_acknowledged_true(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that POST /reminders/{id}/acknowledge sets acknowledged = true."""
        async def mock_acknowledge_reminder(alert_id, user_id):
            return True
        
        monkeypatch.setattr("app.services.reminder_service.acknowledge_reminder", mock_acknowledge_reminder)
        
        response = await client.post(
            "/reminders/alert_123/acknowledge",
            headers=auth_headers
        )
        assert response.status_code == 200


class _async_cursor:
    """Minimal async cursor that yields from a list."""
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration

    def sort(self, *args, **kwargs):
        return self
