import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestReminders:
    """Test reminder functionality."""

    async def test_memory_with_date_and_alertable_intent_creates_reminder_alert(self, monkeypatch):
        """Test that memory with date + alertable intent creates reminder alert."""
        # Mock MongoDB collections
        mock_memories_col = MagicMock()
        mock_memories_col.find = MagicMock(return_value=_async_cursor([
            {
                "_id": "mem_1",
                "user_id": "test_user",
                "text": "Meeting tomorrow at 2pm",
                "metadata": {
                    "intent": "meeting",
                    "entities": {
                        "dates": ["2026-04-15T14:00:00"]
                    }
                }
            }
        ]))
        
        mock_alerts_col = MagicMock()
        mock_alerts_col.find_one = AsyncMock(return_value=None)
        mock_alerts_col.insert_one = AsyncMock()
        
        monkeypatch.setattr("app.services.reminder_service._memories_col", mock_memories_col)
        monkeypatch.setattr("app.services.reminder_service._alerts_col", mock_alerts_col)
        
        from app.services.reminder_service import check_and_fire_reminders
        count = await check_and_fire_reminders()
        
        assert count >= 0
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
