import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealth:
    """Test health check endpoint."""

    async def test_status_returns_ok_when_all_services_up(self, client: AsyncClient, monkeypatch):
        """Test that /status returns ok when all services up."""
        # Mock MongoDB ping
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
        
        # Mock memories collection
        mock_col = MagicMock()
        mock_col.count_documents = AsyncMock(return_value=100)
        
        # Mock get_db
        def mock_get_db():
            return mock_db
        
        # Mock _memories_collection
        def mock_memories_collection():
            return mock_col
        
        # Mock ChromaDB heartbeat
        mock_chroma_client = MagicMock()
        mock_chroma_client.heartbeat = MagicMock()
        
        # Mock Groq
        mock_groq_client = MagicMock()
        mock_groq_client.models.list = AsyncMock(return_value=["model1"])
        
        monkeypatch.setattr("app.config.settings.groq_api_key", "test-groq-key")
        monkeypatch.setattr("app.services.database.get_db", mock_get_db)
        monkeypatch.setattr("app.services.memory_store._memories_collection", mock_memories_collection)
        monkeypatch.setattr("chromadb.PersistentClient", lambda path: mock_chroma_client)
        monkeypatch.setattr("app.services.groq_service.client", mock_groq_client)
        
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["services"]["mongodb"] == "healthy"
        assert data["services"]["chromadb"] == "healthy"
        assert data["services"]["groq"] == "healthy"
        assert data["overall"] == "healthy"

    async def test_status_returns_degraded_if_groq_down(self, client: AsyncClient, monkeypatch):
        """Test that /status returns degraded status if Groq is down."""
        # Mock MongoDB healthy
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
        mock_col = MagicMock()
        mock_col.count_documents = AsyncMock(return_value=100)
        
        def mock_get_db():
            return mock_db
        
        def mock_memories_collection():
            return mock_col
        
        # Mock ChromaDB healthy
        mock_chroma_client = MagicMock()
        mock_chroma_client.heartbeat = MagicMock()
        
        # Mock Groq down
        mock_groq_client = MagicMock()
        mock_groq_client.models.list = AsyncMock(side_effect=Exception("Connection refused"))
        
        monkeypatch.setattr("app.config.settings.groq_api_key", "test-groq-key")
        monkeypatch.setattr("app.services.database.get_db", mock_get_db)
        monkeypatch.setattr("app.services.memory_store._memories_collection", mock_memories_collection)
        monkeypatch.setattr("chromadb.PersistentClient", lambda path: mock_chroma_client)
        monkeypatch.setattr("app.services.groq_service.client", mock_groq_client)
        
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["services"]["mongodb"] == "healthy"
        assert data["services"]["chromadb"] == "healthy"
        assert "unhealthy" in data["services"]["groq"]
        assert data["overall"] == "degraded"

    async def test_status_returns_degraded_if_chromadb_down(self, client: AsyncClient, monkeypatch):
        """Test that /status returns degraded status if ChromaDB is down."""
        # Mock MongoDB healthy
        mock_db = MagicMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
        mock_col = MagicMock()
        mock_col.count_documents = AsyncMock(return_value=100)
        
        def mock_get_db():
            return mock_db
        
        def mock_memories_collection():
            return mock_col
        
        # Mock ChromaDB down
        mock_chroma_client = MagicMock()
        mock_chroma_client.heartbeat = MagicMock(side_effect=Exception("ChromaDB error"))
        
        # Mock Groq healthy
        mock_groq_client = MagicMock()
        mock_groq_client.models.list = AsyncMock(return_value=["model1"])
        
        monkeypatch.setattr("app.config.settings.groq_api_key", "test-groq-key")
        monkeypatch.setattr("app.services.database.get_db", mock_get_db)
        monkeypatch.setattr("app.services.memory_store._memories_collection", mock_memories_collection)
        monkeypatch.setattr("chromadb.PersistentClient", lambda path: mock_chroma_client)
        monkeypatch.setattr("app.services.groq_service.client", mock_groq_client)
        
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["services"]["mongodb"] == "healthy"
        assert "unhealthy" in data["services"]["chromadb"]
        assert data["services"]["groq"] == "healthy"
        assert data["overall"] == "degraded"
