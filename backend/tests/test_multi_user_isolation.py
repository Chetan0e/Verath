import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth import create_access_token


class TestMultiUserIsolation:
    """Security and multi-user data isolation tests."""

    @pytest.mark.asyncio
    async def test_user_cannot_delete_another_users_memory(self, client, monkeypatch):
        """User B must be rejected with 403 when trying to delete User A's memory."""
        user_a_token = create_access_token("user_alice")
        user_b_token = create_access_token("user_bob")

        headers_a = {"Authorization": f"Bearer {user_a_token}"}
        headers_b = {"Authorization": f"Bearer {user_b_token}"}

        # Mock collection find_one to return Alice's memory
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value={
            "_id": "alice-memory-uuid-1234",
            "user_id": "user_alice",
            "text": "Alice secret memory",
        })

        monkeypatch.setattr("app.routes.memories._memories_collection", lambda: mock_col)

        # Bob attempts to delete Alice's memory
        response = await client.delete("/memory/alice-memory-uuid-1234", headers=headers_b)
        assert response.status_code == 403
        assert "You do not have permission" in response.json()["detail"]

        # Alice attempts to delete her own memory
        mock_delete = AsyncMock()
        monkeypatch.setattr("app.routes.memories.delete_memory", mock_delete)

        response_alice = await client.delete("/memory/alice-memory-uuid-1234", headers=headers_a)
        assert response_alice.status_code == 200
        assert response_alice.json()["message"] == "Memory deleted successfully"
        mock_delete.assert_called_once_with("alice-memory-uuid-1234", "user_alice")

    @pytest.mark.asyncio
    async def test_export_is_strictly_scoped_to_requesting_user(self, client, monkeypatch):
        """GET /export must only query and return documents for the authenticated user_id."""
        user_alice_token = create_access_token("alice")
        headers = {"Authorization": f"Bearer {user_alice_token}"}

        captured_query = {}

        async def mock_all_memories_filtered(query):
            captured_query.update(query)
            return [
                {
                    "_id": "mem-1",
                    "user_id": "alice",
                    "text": "Alice notes",
                    "created_at": "2026-10-17T10:00:00",
                    "metadata": {"intent": "note", "importance": 0.8, "speaker": "alice", "summary": "Notes"}
                }
            ]

        monkeypatch.setattr("app.routes.advanced.all_memories_filtered", mock_all_memories_filtered)

        response = await client.get("/export?format=json", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["memories"]) == 1
        assert data["memories"][0]["user_id"] == "alice"
        assert captured_query.get("user_id") == "alice"

    @pytest.mark.asyncio
    async def test_unauthenticated_requests_are_rejected(self, client):
        """Endpoints must reject requests missing auth headers."""
        routes = [
            ("GET", "/export"),
            ("GET", "/timeline"),
            ("GET", "/statistics"),
            ("GET", "/summary"),
            ("GET", "/insights"),
            ("DELETE", "/memory/some-id"),
        ]

        for method, route in routes:
            if method == "GET":
                res = await client.get(route)
            elif method == "DELETE":
                res = await client.delete(route)
            assert res.status_code in (401, 403), f"Route {route} allowed unauthenticated access"
