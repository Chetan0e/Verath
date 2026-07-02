import pytest
from httpx import AsyncClient


# ── Status endpoint ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_status_ok(client: AsyncClient):
    response = await client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── Auth: signup ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_signup_creates_user(client: AsyncClient, mock_db, monkeypatch):
    monkeypatch.setattr("app.services.auth.get_db", lambda: {"users": mock_db, "login_attempts": mock_db})

    response = await client.post("/auth/signup", json={
        "username": "newuser",
        "password": "password123"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"


@pytest.mark.asyncio
async def test_signup_duplicate_rejected(client: AsyncClient, mock_db, monkeypatch):
    from unittest.mock import AsyncMock
    mock_db.find_one = AsyncMock(return_value={"username": "existing"})
    monkeypatch.setattr("app.services.auth.get_db", lambda: {"users": mock_db, "login_attempts": mock_db})

    response = await client.post("/auth/signup", json={
        "username": "existing",
        "password": "password123"
    })
    assert response.status_code == 409


# ── Auth: login ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_login_returns_token_pair(client: AsyncClient, mock_db, monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.auth import hash_password

    mock_db.find_one = AsyncMock(return_value={
        "username": "test_user",
        "password_hash": hash_password("correct_password"),
    })
    monkeypatch.setattr("app.services.auth.get_db", lambda: {"users": mock_db, "login_attempts": mock_db})
    response = await client.post("/auth/login", json={
        "username": "test_user",
        "password": "correct_password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client: AsyncClient, mock_db, monkeypatch):
    from unittest.mock import AsyncMock
    from app.services.auth import hash_password

    mock_db.find_one = AsyncMock(return_value={
        "username": "test_user",
        "password_hash": hash_password("correct_password"),
    })
    monkeypatch.setattr("app.services.auth.get_db", lambda: {"users": mock_db, "login_attempts": mock_db})
    response = await client.post("/auth/login", json={
        "username": "test_user",
        "password": "wrong_password"
    })
    assert response.status_code == 401


# ── Auth: token refresh ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(client: AsyncClient, refresh_token: str):
    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient, access_token: str):
    """Access tokens must not be accepted at the refresh endpoint."""
    response = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


# ── Protected route: unauthenticated ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_query_requires_auth(client: AsyncClient):
    response = await client.get("/query", params={"q": "what did I do today"})
    assert response.status_code == 403


# ── Query endpoint ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_query_returns_answer_and_confidence(
    client: AsyncClient,
    auth_headers: dict,
    mock_chroma,
    mock_embedding,
    monkeypatch,
):
    from unittest.mock import AsyncMock, patch

    monkeypatch.setattr("app.services.query_engine.generate_response", AsyncMock(
        return_value="You had a meeting today."
    ))
    monkeypatch.setattr("app.services.reranker.rerank", lambda query, candidates, top_k: [
        {**candidates[0], "rerank_score": 2.1, "confidence": 0.89}
    ] if candidates else [])

    response = await client.get(
        "/query",
        params={"q": "what did I do today"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence_score" in data
    assert 0.0 <= data["confidence_score"] <= 1.0


# ── Reminders endpoint ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_reminders_upcoming_returns_list(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch,
):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(
        "app.routes.reminders.get_upcoming_reminders",
        AsyncMock(return_value=[])
    )
    response = await client.get("/reminders/upcoming", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["count"] == 0
