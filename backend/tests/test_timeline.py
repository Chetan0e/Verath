import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from app.services.timeline import get_today_timeline, get_date_timeline, get_recent_timeline

class TestTimeline:
    """Test timeline generation and metadata extraction."""

    @pytest.mark.asyncio
    async def test_timeline_metadata_extraction(self, monkeypatch):
        """Verify that speaker, importance, tags, and cleaned text are populated correctly from metadata."""
        
        # Mock memory document with data nested under metadata
        now = datetime.utcnow()
        mock_memories = [
            {
                "_id": "mock_id_1",
                "created_at": now,
                "timestamp": now.isoformat(),
                "text": "Fallback text",
                "metadata": {
                    "cleaned_text": "Extracted cleaned text",
                    "speaker": "John Doe",
                    "importance": 0.9,
                    "tags": ["work", "important"],
                    "intent": "meeting"
                }
            }
        ]

        async def mock_all_memories(user_id, limit=1000):
            return mock_memories

        monkeypatch.setattr("app.services.timeline.all_memories", mock_all_memories)

        # 1. Test get_today_timeline
        today_timeline = await get_today_timeline("user_123")
        assert len(today_timeline) == 1
        assert today_timeline[0]["text"] == "Extracted cleaned text"
        assert today_timeline[0]["speaker"] == "John Doe"
        assert today_timeline[0]["importance"] == 0.9
        assert today_timeline[0]["tags"] == ["work", "important"]
        assert today_timeline[0]["intent"] == "meeting"
        assert today_timeline[0]["id"] == "mock_id_1"

        # 2. Test get_recent_timeline
        recent_timeline = await get_recent_timeline("user_123", hours=24)
        assert len(recent_timeline) == 1
        assert recent_timeline[0]["text"] == "Extracted cleaned text"
        assert recent_timeline[0]["speaker"] == "John Doe"
        assert recent_timeline[0]["importance"] == 0.9
        assert recent_timeline[0]["tags"] == ["work", "important"]
        assert recent_timeline[0]["intent"] == "meeting"
        assert recent_timeline[0]["id"] == "mock_id_1"

        # 3. Test get_date_timeline
        date_str = now.strftime("%Y-%m-%d")
        date_timeline = await get_date_timeline("user_123", date_str)
        assert len(date_timeline) == 1
        assert date_timeline[0]["text"] == "Extracted cleaned text"
        assert date_timeline[0]["speaker"] == "John Doe"
        assert date_timeline[0]["importance"] == 0.9
        assert date_timeline[0]["tags"] == ["work", "important"]
        assert date_timeline[0]["intent"] == "meeting"
        assert date_timeline[0]["id"] == "mock_id_1"

    @pytest.mark.asyncio
    async def test_timeline_metadata_fallback(self, monkeypatch):
        """Verify fallback behaviors when metadata is missing or empty."""
        
        now = datetime.utcnow()
        mock_memories = [
            {
                "_id": "mock_id_2",
                "created_at": now,
                "timestamp": now.isoformat(),
                "text": "Fallback text only",
                # No metadata provided or empty metadata
            }
        ]

        async def mock_all_memories(user_id, limit=1000):
            return mock_memories

        monkeypatch.setattr("app.services.timeline.all_memories", mock_all_memories)

        # 1. Test get_today_timeline fallbacks
        today_timeline = await get_today_timeline("user_123")
        assert len(today_timeline) == 1
        assert today_timeline[0]["text"] == "Fallback text only"
        assert today_timeline[0]["speaker"] == "You"
        assert today_timeline[0]["importance"] == 0.5
        assert today_timeline[0]["tags"] == []

        # 2. Test get_recent_timeline fallbacks
        recent_timeline = await get_recent_timeline("user_123", hours=24)
        assert len(recent_timeline) == 1
        assert recent_timeline[0]["text"] == "Fallback text only"
        assert recent_timeline[0]["speaker"] == "You"  # get_recent_timeline uses "You" as fallback
        assert recent_timeline[0]["importance"] == 0.5
        assert recent_timeline[0]["tags"] == []

        # 3. Test get_date_timeline fallbacks
        date_str = now.strftime("%Y-%m-%d")
        date_timeline = await get_date_timeline("user_123", date_str)
        assert len(date_timeline) == 1
        assert date_timeline[0]["text"] == "Fallback text only"
        assert date_timeline[0]["speaker"] == "You"  # get_date_timeline uses "You" as fallback
        assert date_timeline[0]["importance"] == 0.5
        assert date_timeline[0]["tags"] == []
