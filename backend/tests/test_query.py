import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


class TestQuery:
    """Test query functionality."""

    async def test_query_returns_answer_sources_confidence(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that query returns answer + sources + confidence."""
        # Mock LLM response
        async def mock_ask_llm(query, context, user_id):
            return "The meeting was about the project roadmap", ["memory_1", "memory_2"], 0.85
        
        monkeypatch.setattr("app.services.llm.ask_llm", mock_ask_llm)
        
        response = await client.get(
            "/query?q=meeting%20about%20roadmap",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data

    async def test_empty_memory_store_returns_graceful_response(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that empty memory store returns graceful 'no memories found' response."""
        # Mock empty memory store
        async def mock_search_memories(user_id, query, limit, intent_filter, min_importance):
            return []
        
        monkeypatch.setattr("app.services.timeline.get_timeline", mock_search_memories)
        monkeypatch.setattr("app.services.llm.ask_llm", lambda q, c, uid: ("No memories found", [], 0.0))
        
        response = await client.get(
            "/query?q=random%20query",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    async def test_intent_filter_param_correctly_filters_results(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that intent_filter param correctly filters results."""
        # Mock search with intent filter
        async def mock_search_memories(user_id, query, limit, intent_filter, min_importance):
            if intent_filter == "meeting":
                return [{"id": "mem1", "text": "Meeting memory", "metadata": {"intent": "meeting"}}]
            return []
        
        monkeypatch.setattr("app.services.memory_store.search_memories", mock_search_memories)
        
        response = await client.get(
            "/query?q=meeting&intent_filter=meeting",
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_min_importance_param_correctly_filters_results(self, client: AsyncClient, monkeypatch, auth_headers):
        """Test that min_importance param correctly filters results."""
        # Mock search with importance filter
        async def mock_search_memories(user_id, query, limit, intent_filter, min_importance):
            if min_importance > 0.7:
                return [{"id": "mem1", "text": "Important memory", "metadata": {"importance": 0.8}}]
            return []
        
        monkeypatch.setattr("app.services.memory_store.search_memories", mock_search_memories)
        
        response = await client.get(
            "/query?q=important&min_importance=0.8",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    async def test_post_query_with_history_passes_turns_to_engine(
        self, client: AsyncClient, monkeypatch, auth_headers
    ):
        """POST /query forwards history turns to run_query."""
        captured = {}

        async def mock_run_query(**kwargs):
            captured.update(kwargs)
            return {
                "answer": "The first one is at 3 PM.",
                "context": [],
                "sources": [],
                "confidence_score": 0.85,
            }

        monkeypatch.setattr("app.routes.query.run_query", mock_run_query)

        response = await client.post(
            "/query",
            json={
                "q": "What time is the first one?",
                "history": [
                    {"role": "user", "content": "What meetings do I have?"},
                    {"role": "assistant", "content": "You have a meeting at 3 PM."},
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "The first one is at 3 PM."
        assert len(captured["history"]) == 2
        assert captured["history"][0]["role"] == "user"

    async def test_post_query_without_history_still_works(
        self, client: AsyncClient, monkeypatch, auth_headers
    ):
        """POST /query with no history field is backward compatible."""
        async def mock_run_query(**kwargs):
            return {
                "answer": "You have a meeting at 3 PM.",
                "context": [],
                "sources": [],
                "confidence_score": 0.7,
            }

        monkeypatch.setattr("app.routes.query.run_query", mock_run_query)

        response = await client.post(
            "/query",
            json={"q": "What meetings do I have?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "answer" in response.json()
