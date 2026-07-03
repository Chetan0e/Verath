import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import app.services.auth as auth_service


class _FakeAttemptsCollection:
    """Stateful in-memory stand-in for the login_attempts MongoDB collection.

    Lets the route-level test exercise the full login -> lockout flow without
    a real Mongo connection while preserving state across requests.
    """

    def __init__(self):
        self._records = {}

    async def find_one(self, query):
        return self._records.get(query["username"])

    async def update_one(self, query, update, upsert=False):
        username = query["username"]
        if username not in self._records and upsert:
            self._records[username] = {"username": username}
        if username in self._records:
            self._records[username].update(update.get("$set", {}))
        return MagicMock(modified_count=1)

    async def delete_one(self, query):
        existed = self._records.pop(query["username"], None) is not None
        return MagicMock(deleted_count=1 if existed else 0)


class TestAccountLockout:
    """Per-account login lockout logic in app.services.auth (issue #55)."""

    @pytest.fixture
    def attempts_col(self, monkeypatch):
        col = MagicMock()
        col.find_one = AsyncMock(return_value=None)
        col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=col)
        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)
        return col

    async def test_no_record_means_not_locked(self, attempts_col):
        assert await auth_service.get_lockout_seconds_remaining("alice") == 0

    async def test_active_lockout_returns_seconds_remaining(self, attempts_col):
        attempts_col.find_one = AsyncMock(return_value={
            "username": "alice",
            "failures": 5,
            "locked_until": datetime.utcnow() + timedelta(minutes=10),
        })
        remaining = await auth_service.get_lockout_seconds_remaining("alice")
        assert 0 < remaining <= 600

    async def test_expired_lockout_returns_zero(self, attempts_col):
        attempts_col.find_one = AsyncMock(return_value={
            "username": "alice",
            "failures": 5,
            "locked_until": datetime.utcnow() - timedelta(seconds=1),
        })
        assert await auth_service.get_lockout_seconds_remaining("alice") == 0

    async def test_failure_below_threshold_increments_without_locking(self, attempts_col, monkeypatch):
        monkeypatch.setattr(auth_service.settings, "login_max_failures", 5)
        attempts_col.find_one = AsyncMock(return_value={"username": "alice", "failures": 1})

        await auth_service.register_failed_login("alice")

        set_doc = attempts_col.update_one.call_args[0][1]["$set"]
        assert set_doc["failures"] == 2
        assert "locked_until" not in set_doc
        assert attempts_col.update_one.call_args.kwargs.get("upsert") is True

    async def test_failure_at_threshold_locks_account(self, attempts_col, monkeypatch):
        monkeypatch.setattr(auth_service.settings, "login_max_failures", 3)
        monkeypatch.setattr(auth_service.settings, "login_lockout_minutes", 15)
        attempts_col.find_one = AsyncMock(return_value={"username": "alice", "failures": 2})

        await auth_service.register_failed_login("alice")

        set_doc = attempts_col.update_one.call_args[0][1]["$set"]
        assert set_doc["failures"] == 3
        assert "locked_until" in set_doc
        assert set_doc["locked_until"] > datetime.utcnow()

    async def test_first_failure_on_fresh_account_increments_from_zero(self, attempts_col, monkeypatch):
        monkeypatch.setattr(auth_service.settings, "login_max_failures", 5)
        attempts_col.find_one = AsyncMock(return_value=None)

        await auth_service.register_failed_login("alice")

        set_doc = attempts_col.update_one.call_args[0][1]["$set"]
        assert set_doc["failures"] == 1

    async def test_successful_login_clears_record(self, attempts_col):
        await auth_service.reset_login_attempts("alice")
        attempts_col.delete_one.assert_awaited_once_with({"username": "alice"})

    async def test_username_is_normalized(self, attempts_col):
        await auth_service.get_lockout_seconds_remaining("  ALICE  ")
        attempts_col.find_one.assert_awaited_once_with({"username": "alice"})

    async def test_login_route_returns_429_after_threshold(self, client, monkeypatch):
        """End-to-end: failures land 401, the (N+1)th request lands 429 with Retry-After."""
        fake_col = _FakeAttemptsCollection()

        # Route handler also calls get_db() for audit_logs and blacklisted_tokens;
        # provide async-safe stubs so those calls don't hit a real server.
        audit_col = MagicMock()
        audit_col.insert_one = AsyncMock()
        blacklist_col = MagicMock()
        blacklist_col.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "login_attempts": fake_col,
            "audit_logs": audit_col,
            "blacklisted_tokens": blacklist_col,
        }.get(name, MagicMock()))

        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)
        monkeypatch.setattr(auth_service.settings, "login_max_failures", 3)
        monkeypatch.setattr(auth_service.settings, "login_lockout_minutes", 15)

        async def always_fail(username, password):
            return None

        # The route does `from app.services.auth import authenticate_user`,
        # so the live binding is on app.routes.auth — patch it there.
        monkeypatch.setattr("app.routes.auth.authenticate_user", always_fail)

        for attempt in range(3):
            resp = await client.post(
                "/auth/login",
                json={"username": "bob", "password": "wrong"},
            )
            assert resp.status_code == 401, (
                f"attempt {attempt + 1} should be 401, got {resp.status_code}: {resp.text}"
            )

        resp = await client.post(
            "/auth/login",
            json={"username": "bob", "password": "wrong"},
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert int(resp.headers["Retry-After"]) > 0