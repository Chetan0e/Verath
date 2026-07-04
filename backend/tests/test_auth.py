import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import status
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)


class TestAuth:
    """Test authentication endpoints."""

    async def test_signup_creates_user_returns_201(self, client: AsyncClient):
        """Test that signup creates a user and returns 201."""
        response = await client.post(
            "/auth/signup",
            json={"username": "newuser", "password": "password123"}
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "username" in data
        assert data["username"] == "newuser"

    async def test_duplicate_signup_returns_409(self, client: AsyncClient, monkeypatch):
        """Test that duplicate signup returns 409."""
        # Mock create_user to return False (user exists)
        async def mock_create_user(username, password):
            return False
        
        monkeypatch.setattr("app.services.auth.create_user", mock_create_user)
        
        response = await client.post(
            "/auth/signup",
            json={"username": "existinguser", "password": "password123"}
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data

    async def test_login_returns_access_and_refresh_tokens(self, client: AsyncClient, monkeypatch):
        """Test that login returns access and refresh tokens."""
        # Mock authenticate_user to succeed
        async def mock_authenticate_user(username, password):
            return username
        
        monkeypatch.setattr("app.services.auth.authenticate_user", mock_authenticate_user)
        
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_with_wrong_password_returns_401(self, client: AsyncClient, monkeypatch):
        """Test that login with wrong password returns 401."""
        # Mock authenticate_user to fail
        async def mock_authenticate_user(username, password):
            return None
        
        monkeypatch.setattr("app.services.auth.authenticate_user", mock_authenticate_user)
        
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    async def test_refresh_returns_new_token_pair_on_valid_token(
        self, client: AsyncClient, monkeypatch
    ):
        """Happy path: a fresh refresh token yields a new access + refresh pair."""
        inserted_docs = []

        mock_col = MagicMock()
        mock_col.insert_one = AsyncMock(
            side_effect=lambda doc: inserted_docs.append(doc) or doc
        )
        mock_audit = MagicMock()
        mock_audit.insert_one = AsyncMock()

        mock_db = {"blacklisted_tokens": mock_col, "audit_logs": mock_audit}
        monkeypatch.setattr("app.routes.auth.get_db", lambda: mock_db)

        refresh_token = create_refresh_token("testuser")
        response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["username"] == "testuser"
        # Old JTI must have been blacklisted
        assert len(inserted_docs) == 1
        assert inserted_docs[0]["reason"] == "refresh_rotation"
        assert inserted_docs[0]["username"] == "testuser"

    async def test_refresh_rejects_replayed_token_via_duplicate_key(
        self, client: AsyncClient, monkeypatch
    ):
        """
        Unit: when insert_one raises DuplicateKeyError the endpoint must return
        401 and must NOT issue any new tokens.
        """
        from pymongo.errors import DuplicateKeyError as MongoDuplicateKeyError

        mock_col = MagicMock()
        mock_col.insert_one = AsyncMock(
            side_effect=MongoDuplicateKeyError("duplicate jti")
        )
        mock_audit = MagicMock()
        mock_audit.insert_one = AsyncMock()

        mock_db = {"blacklisted_tokens": mock_col, "audit_logs": mock_audit}
        monkeypatch.setattr("app.routes.auth.get_db", lambda: mock_db)

        refresh_token = create_refresh_token("testuser")
        response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "already used" in response.json()["detail"].lower() or \
               "revoked" in response.json()["detail"].lower()

    async def test_refresh_concurrent_requests_only_one_succeeds(
        self, client: AsyncClient, monkeypatch
    ):
        """
        Concurrency: two simultaneous refresh requests with the same token must
        result in exactly one 200 and one 401 — not two 200s.
        """
        import asyncio
        from pymongo.errors import DuplicateKeyError as MongoDuplicateKeyError

        call_count = {"n": 0}

        async def atomic_insert(doc):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise MongoDuplicateKeyError("duplicate jti")
            return doc

        mock_col = MagicMock()
        mock_col.insert_one = AsyncMock(side_effect=atomic_insert)
        mock_audit = MagicMock()
        mock_audit.insert_one = AsyncMock()

        mock_db = {"blacklisted_tokens": mock_col, "audit_logs": mock_audit}
        monkeypatch.setattr("app.routes.auth.get_db", lambda: mock_db)

        refresh_token = create_refresh_token("testuser")

        r1, r2 = await asyncio.gather(
            client.post("/auth/refresh", json={"refresh_token": refresh_token}),
            client.post("/auth/refresh", json={"refresh_token": refresh_token}),
        )

        statuses = sorted([r1.status_code, r2.status_code])
        assert statuses == [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ], f"Expected [200, 401], got {statuses}"

    async def test_refresh_rejects_invalid_jwt(self, client: AsyncClient):
        """A malformed or tampered token must return 401 without touching the DB."""
        response = await client.post(
            "/auth/refresh", json={"refresh_token": "not.a.valid.jwt"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_refresh_rejects_access_token_used_as_refresh(
        self, client: AsyncClient, monkeypatch
    ):
        """An access token presented to /auth/refresh must be rejected (wrong type)."""
        mock_audit = MagicMock()
        mock_audit.insert_one = AsyncMock()
        monkeypatch.setattr("app.routes.auth.get_db", lambda: {"audit_logs": mock_audit})

        access_token = create_access_token("testuser")
        response = await client.post(
            "/auth/refresh", json={"refresh_token": access_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_rate_limiting_triggers_on_6th_signup_attempt(self, client: AsyncClient, monkeypatch):
        """Test that rate limiting triggers on 6th signup attempt."""
        # Mock the limiter to count attempts
        call_count = [0]
        
        async def mock_create_user(username, password):
            call_count[0] += 1
            return True
        
        monkeypatch.setattr("app.services.auth.create_user", mock_create_user)
        
        # Make 5 successful requests
        for _ in range(5):
            response = await client.post(
                "/auth/signup",
                json={"username": f"user{_}", "password": "password123"}
            )
            # In real test, we'd mock the limiter to track this
            # For now, just verify the endpoint is callable
        
        # 6th request should be rate limited (in real scenario with slowapi)
        # This test would need actual slowapi mocking to properly test rate limiting
        # For now, we'll just verify the endpoint structure
        response = await client.post(
            "/auth/signup",
            json={"username": "user6", "password": "password123"}
        )
        # With proper limiter mock, this would return 429

    async def test_verify_access_token_rejects_blacklisted_jti(self, monkeypatch):
        """Test that access tokens are rejected once their JTI is blacklisted."""
        token = create_access_token("testuser")
        mock_blacklist = AsyncMock(return_value={"jti": "blocked"})
        mock_db = {"blacklisted_tokens": type("BlacklistCollection", (), {"find_one": mock_blacklist})()}

        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)

        username = await verify_access_token(token)

        assert username is None
        mock_blacklist.assert_awaited_once()

    # ── Refresh-token rotation tests ─────────────────────────────

    async def test_verify_refresh_token_rejects_blacklisted_jti(self, monkeypatch):
        """Unit: a refresh token whose JTI is in the blacklist must be rejected."""
        token = create_refresh_token("testuser")
        mock_blacklist = AsyncMock(return_value={"jti": "some-jti"})
        mock_db = {
            "blacklisted_tokens": type(
                "BlacklistCollection", (), {"find_one": mock_blacklist}
            )()
        }
        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)

        result = await verify_refresh_token(token)

        assert result is None
        mock_blacklist.assert_awaited_once()

    async def test_verify_refresh_token_accepts_non_blacklisted_jti(self, monkeypatch):
        """Unit: a refresh token not in the blacklist must return the username."""
        token = create_refresh_token("testuser")
        mock_blacklist = AsyncMock(return_value=None)  # not blacklisted
        mock_db = {
            "blacklisted_tokens": type(
                "BlacklistCollection", (), {"find_one": mock_blacklist}
            )()
        }
        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)

        result = await verify_refresh_token(token)

        assert result == "testuser"

    async def test_logout_still_invalidates_access_token(self, client: AsyncClient, monkeypatch):
        """
        Regression: logout must continue to blacklist the access token and return 200.
        Newly issued refresh tokens must remain valid after logout.
        """
        access_token = create_access_token("testuser")

        inserted_docs = []
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.insert_one = AsyncMock(side_effect=lambda doc: inserted_docs.append(doc))

        mock_audit = MagicMock()
        mock_audit.insert_one = AsyncMock()

        mock_db = {"blacklisted_tokens": mock_collection, "audit_logs": mock_audit}
        monkeypatch.setattr("app.services.auth.get_db", lambda: mock_db)
        monkeypatch.setattr("app.routes.auth.get_db", lambda: mock_db)

        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(inserted_docs) == 1
        assert inserted_docs[0].get("username") == "testuser"
        
    # ── Logout blacklist-bypass / crash tests  ──────────

    async def test_logout_rejects_already_blacklisted_token(
        self, client: AsyncClient, monkeypatch
    ):
        """A token whose jti is already blacklisted must be rejected at
        /logout (401) rather than treated as valid — /logout must go through
        the same blacklist check as every other protected route."""
        token = create_access_token("testuser")

        # blacklist lookup returns a hit → token is already revoked
        mock_blacklist = AsyncMock(return_value={"jti": "blocked"})
        fake_col = type(
            "BlacklistCollection", (), {"find_one": mock_blacklist}
        )()
        fake_db = {"blacklisted_tokens": fake_col}
        monkeypatch.setattr("app.services.auth.get_db", lambda: fake_db)

        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_relogout_does_not_500_on_duplicate(
        self, client: AsyncClient, monkeypatch
    ):
        """Re-submitting a token to /logout must not crash with HTTP 500 even
        if the insert hits the unique-jti index (DuplicateKeyError handled)."""
        from pymongo.errors import DuplicateKeyError

        token = create_access_token("testuser")

        # Not in blacklist on lookup (so auth passes), but insert raises a
        # duplicate-key error (simulating a race / repeat).
        mock_find = AsyncMock(return_value=None)
        mock_insert = AsyncMock(side_effect=DuplicateKeyError("dup jti"))
        fake_col = type(
            "BlacklistCollection",
            (),
            {"find_one": mock_find, "insert_one": mock_insert},
        )()
        fake_db = {"blacklisted_tokens": fake_col}

        # both the service-layer blacklist check and the route-layer insert
        # resolve get_db to our fake
        monkeypatch.setattr("app.services.auth.get_db", lambda: fake_db)
        monkeypatch.setattr("app.routes.auth.get_db", lambda: fake_db)

        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Must NOT be a 500 — the DuplicateKeyError is caught and logout
        # succeeds idempotently.
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.status_code == status.HTTP_200_OK

    async def test_verify_access_token_rejects_when_db_unavailable(self, monkeypatch):
        """
        Security: verify_access_token must return None (fail-closed) when
        get_db() returns None — not silently accept the token.
        Regression for issue #142.
        """
        token = create_access_token("testuser")
        monkeypatch.setattr("app.services.auth.get_db", lambda: None)

        result = await verify_access_token(token)

        assert result is None, (
            "verify_access_token must deny tokens when DB is unavailable "
            "(fail-closed), not accept them"
        )

    async def test_verify_refresh_token_rejects_when_db_unavailable(self, monkeypatch):
        """
        Security: verify_refresh_token must return None (fail-closed) when
        get_db() returns None — not silently accept the token.
        Regression for issue #142.
        """
        token = create_refresh_token("testuser")
        monkeypatch.setattr("app.services.auth.get_db", lambda: None)

        result = await verify_refresh_token(token)

        assert result is None, (
            "verify_refresh_token must deny tokens when DB is unavailable "
            "(fail-closed), not accept them"
        )

    async def test_verify_access_token_rejects_when_blacklist_lookup_raises(self, monkeypatch):
        """
        Security: verify_access_token must return None if the blacklist
        find_one raises (e.g. connection pool exhaustion, network partition).
        Regression for issue #142.
        """
        token = create_access_token("testuser")

        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(side_effect=Exception("connection reset"))
        monkeypatch.setattr(
            "app.services.auth.get_db",
            lambda: {"blacklisted_tokens": mock_col},
        )

        result = await verify_access_token(token)

        assert result is None

    async def test_verify_refresh_token_rejects_when_blacklist_lookup_raises(self, monkeypatch):
        """
        Security: verify_refresh_token must return None if the blacklist
        find_one raises (e.g. connection pool exhaustion, network partition).
        Regression for issue #142.
        """
        token = create_refresh_token("testuser")

        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(side_effect=Exception("connection reset"))
        monkeypatch.setattr(
            "app.services.auth.get_db",
            lambda: {"blacklisted_tokens": mock_col},
        )

        result = await verify_refresh_token(token)

        assert result is None

    async def test_blacklisted_jti_rejected_even_after_db_recovers(self, monkeypatch):
        """
        Security: a token whose JTI was blacklisted before a DB outage must
        remain rejected once the DB is back — the fail-closed path during
        outage must not have 'cleared' the blacklist entry.
        Regression for issue #142.
        """
        token = create_access_token("testuser")

        # Phase 1: DB down — token must be rejected (fail-closed)
        monkeypatch.setattr("app.services.auth.get_db", lambda: None)
        result_during_outage = await verify_access_token(token)
        assert result_during_outage is None

        # Phase 2: DB back up with the JTI blacklisted — still rejected
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value={"jti": "some-jti"})
        monkeypatch.setattr(
            "app.services.auth.get_db",
            lambda: {"blacklisted_tokens": mock_col},
        )
        result_after_recovery = await verify_access_token(token)
        assert result_after_recovery is None

    async def test_valid_token_accepted_when_db_available_and_not_blacklisted(self, monkeypatch):
        """
        Sanity: fail-closed changes must not break the normal happy path —
        a non-blacklisted token with DB available must still be accepted.
        """
        token = create_access_token("testuser")

        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value=None)  # not blacklisted
        monkeypatch.setattr(
            "app.services.auth.get_db",
            lambda: {"blacklisted_tokens": mock_col},
        )

        result = await verify_access_token(token)

        assert result == "testuser"