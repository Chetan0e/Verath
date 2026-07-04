import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


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


def _make_db(collections):
    """Return a mock db whose [name] indexing yields the given mock collections."""
    db = MagicMock()
    db.__getitem__.side_effect = lambda name: collections[name]
    return db


class TestDigestService:
    """Unit tests for the digest service helpers."""

    async def test_generate_and_store_digest_persists_summary(self, monkeypatch):
        """generate_and_store_digest should call the summarizer and insert a digest doc."""
        digests = MagicMock()
        digests.insert_one = AsyncMock()
        db = _make_db({"digests": digests})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        async def mock_generate_period_summary(user_id, hours=24):
            return "You logged 3 memories this week."

        monkeypatch.setattr(
            "app.services.digest.generate_period_summary",
            mock_generate_period_summary,
        )

        from app.services.digest import generate_and_store_digest

        doc = await generate_and_store_digest("test_user", window_hours=168)

        assert doc["user_id"] == "test_user"
        assert doc["window_hours"] == 168
        assert doc["summary"] == "You logged 3 memories this week."
        digests.insert_one.assert_called_once()

    async def test_generate_and_store_digest_empty_memory_fallback(self, monkeypatch):
        """The summarizer's empty-window string should flow through to the stored digest."""
        digests = MagicMock()
        digests.insert_one = AsyncMock()
        db = _make_db({"digests": digests})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        async def mock_generate_period_summary(user_id, hours=24):
            return f"No memories recorded in the last {hours} hours."

        monkeypatch.setattr(
            "app.services.digest.generate_period_summary",
            mock_generate_period_summary,
        )

        from app.services.digest import generate_and_store_digest

        doc = await generate_and_store_digest("test_user", window_hours=168)

        assert "No memories recorded" in doc["summary"]
        digests.insert_one.assert_called_once()

    async def test_get_latest_digest_returns_most_recent(self, monkeypatch):
        """get_latest_digest should query by user_id sorted by generated_at desc."""
        latest = {
            "user_id": "test_user",
            "generated_at": datetime.utcnow(),
            "window_hours": 168,
            "summary": "Latest digest.",
        }
        digests = MagicMock()
        digests.find_one = AsyncMock(return_value=latest)
        db = _make_db({"digests": digests})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        from app.services.digest import get_latest_digest

        result = await get_latest_digest("test_user")

        assert result == latest
        digests.find_one.assert_called_once()

    async def test_run_weekly_digests_only_processes_active_users(self, monkeypatch):
        """run_weekly_digests should only digest users with recent memory activity."""
        memories = MagicMock()
        memories.distinct = AsyncMock(return_value=["user_1", "user_2"])
        db = _make_db({"memories": memories})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        generated_for = []

        async def mock_generate_and_store_digest(user_id, window_hours=168):
            generated_for.append(user_id)
            return {"user_id": user_id}

        monkeypatch.setattr(
            "app.services.digest.generate_and_store_digest",
            mock_generate_and_store_digest,
        )

        from app.services.digest import run_weekly_digests

        count = await run_weekly_digests()

        assert count == 2
        assert generated_for == ["user_1", "user_2"]
        memories.distinct.assert_called_once()

    async def test_get_active_user_ids_queries_created_at_not_timestamp(self, monkeypatch):
        """The active-user query must filter on created_at (BSON Date), not the
        timestamp string field, or it silently matches nothing in MongoDB."""
        memories = MagicMock()
        memories.distinct = AsyncMock(return_value=["user_1"])
        db = _make_db({"memories": memories})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        from app.services.digest import _get_active_user_ids

        result = await _get_active_user_ids(168)

        assert result == ["user_1"]
        memories.distinct.assert_called_once()
        field, query = memories.distinct.call_args.args
        assert field == "user_id"
        assert "created_at" in query
        assert "timestamp" not in query

    async def test_run_weekly_digests_skips_inactive_users(self, monkeypatch):
        """With no active users, no digests are generated."""
        memories = MagicMock()
        memories.distinct = AsyncMock(return_value=[])
        db = _make_db({"memories": memories})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        from app.services.digest import run_weekly_digests

        count = await run_weekly_digests()

        assert count == 0

    async def test_run_weekly_digests_skips_failing_user(self, monkeypatch):
        """A failure for one user should not stop the others; count reflects successes."""
        memories = MagicMock()
        memories.distinct = AsyncMock(return_value=["user_1", "user_2"])
        db = _make_db({"memories": memories})
        monkeypatch.setattr("app.services.digest.get_db", lambda: db)

        async def mock_generate_and_store_digest(user_id, window_hours=168):
            if user_id == "user_1":
                raise RuntimeError("summarizer boom")
            return {"user_id": user_id}

        monkeypatch.setattr(
            "app.services.digest.generate_and_store_digest",
            mock_generate_and_store_digest,
        )

        from app.services.digest import run_weekly_digests

        count = await run_weekly_digests()

        assert count == 1


class TestDigestEndpoints:
    """Endpoint tests for the digest routes on the advanced router."""

    async def test_latest_digest_returns_404_when_none(
        self, client: AsyncClient, monkeypatch, auth_headers
    ):
        """GET /digest/latest should 404 when no digest exists yet."""
        async def mock_get_latest_digest(user_id):
            return None

        monkeypatch.setattr(
            "app.routes.advanced.get_latest_digest", mock_get_latest_digest
        )

        response = await client.get("/digest/latest", headers=auth_headers)
        assert response.status_code == 404

    async def test_latest_digest_returns_digest(
        self, client: AsyncClient, monkeypatch, auth_headers
    ):
        """GET /digest/latest should return the stored digest fields."""
        async def mock_get_latest_digest(user_id):
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow(),
                "window_hours": 168,
                "summary": "Your week in review.",
            }

        monkeypatch.setattr(
            "app.routes.advanced.get_latest_digest", mock_get_latest_digest
        )

        response = await client.get("/digest/latest", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Your week in review."
        assert data["window_hours"] == 168

    async def test_trigger_digest_generates_and_returns_summary(
        self, client: AsyncClient, monkeypatch, auth_headers
    ):
        """POST /digest/generate should generate a digest and return its summary."""
        async def mock_generate_and_store_digest(user_id, window_hours=168):
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow(),
                "window_hours": window_hours,
                "summary": "Freshly generated.",
            }

        monkeypatch.setattr(
            "app.routes.advanced.generate_and_store_digest",
            mock_generate_and_store_digest,
        )

        response = await client.post("/digest/generate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Freshly generated."

    async def test_trigger_digest_rejects_out_of_range_window(
        self, client: AsyncClient, auth_headers
    ):
        """window_hours outside the allowed range should 422 from query validation."""
        response = await client.post(
            "/digest/generate?window_hours=0", headers=auth_headers
        )
        assert response.status_code == 422