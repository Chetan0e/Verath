import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStoreMemoriesBatch:
    """Regression tests for store_memories_batch return value fix (#70)."""

    async def test_returns_list_of_uuids_on_success(self, monkeypatch):
        """store_memories_batch must return a list of N UUIDs, not None."""
        mock_col = MagicMock()
        mock_col.insert_many = AsyncMock(return_value=MagicMock())

        mock_chroma_col = MagicMock()
        mock_chroma_col.upsert = MagicMock()

        monkeypatch.setattr(
            "app.services.memory_store._memories_collection",
            lambda: mock_col
        )
        monkeypatch.setattr(
            "app.services.memory_store._get_collection",
            lambda user_id: mock_chroma_col
        )
        monkeypatch.setattr(
            "app.services.memory_store.get_embeddings_batch",
            AsyncMock(return_value=[[0.1] * 768, [0.1] * 768])
        )

        from app.services.memory_store import store_memories_batch

        items = [
            {"text": "First memory", "metadata": {"intent": "meeting", "speaker": "user", "importance": 0.7}},
            {"text": "Second memory", "metadata": {"intent": "task", "speaker": "user", "importance": 0.5}},
        ]

        result = await store_memories_batch(user_id="test_user", items=items)

        assert result is not None, "Expected a list of IDs, got None"
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) == 2, f"Expected 2 IDs, got {len(result)}"
        for mem_id in result:
            assert isinstance(mem_id, str) and len(mem_id) == 36, (
                f"Expected UUID string, got: {mem_id}"
            )

    async def test_returned_ids_match_mongodb_insert(self, monkeypatch):
        """Returned IDs must match the _id values inserted into MongoDB."""
        inserted_docs = []

        mock_col = MagicMock()
        async def capture_insert_many(docs):
            inserted_docs.extend(docs)
            return MagicMock()
        mock_col.insert_many = capture_insert_many

        mock_chroma_col = MagicMock()
        mock_chroma_col.upsert = MagicMock()

        monkeypatch.setattr(
            "app.services.memory_store._memories_collection",
            lambda: mock_col
        )
        monkeypatch.setattr(
            "app.services.memory_store._get_collection",
            lambda user_id: mock_chroma_col
        )
        monkeypatch.setattr(
            "app.services.memory_store.get_embeddings_batch",
            AsyncMock(return_value=[[0.1] * 768, [0.1] * 768])
        )

        from app.services.memory_store import store_memories_batch

        items = [
            {"text": "Alpha", "metadata": {"intent": "task", "speaker": "user", "importance": 0.6}},
            {"text": "Beta",  "metadata": {"intent": "task", "speaker": "user", "importance": 0.4}},
        ]

        result = await store_memories_batch(user_id="test_user", items=items)

        mongo_ids = [doc["_id"] for doc in inserted_docs]
        assert sorted(result) == sorted(mongo_ids), (
            f"Returned IDs {result} don't match inserted IDs {mongo_ids}"
        )

    async def test_rollback_on_chromadb_failure(self, monkeypatch):
        """On ChromaDB failure, MongoDB docs must be rolled back and exception raised."""
        mock_col = MagicMock()
        mock_col.insert_many = AsyncMock(return_value=MagicMock())
        mock_col.delete_many = AsyncMock(return_value=MagicMock())

        mock_chroma_col = MagicMock()
        mock_chroma_col.upsert = MagicMock(side_effect=RuntimeError("ChromaDB down"))

        monkeypatch.setattr(
            "app.services.memory_store._memories_collection",
            lambda: mock_col
        )
        monkeypatch.setattr(
            "app.services.memory_store._get_collection",
            lambda user_id: mock_chroma_col
        )
        monkeypatch.setattr(
            "app.services.memory_store.get_embeddings_batch",
            AsyncMock(return_value=[[0.1] * 768, [0.1] * 768])
        )

        from app.services.memory_store import store_memories_batch

        items = [
            {"text": "Memory A", "metadata": {"intent": "meeting", "speaker": "user", "importance": 0.8}},
            {"text": "Memory B", "metadata": {"intent": "task",    "speaker": "user", "importance": 0.5}},
        ]

        with pytest.raises(RuntimeError, match="ChromaDB down"):
            await store_memories_batch(user_id="test_user", items=items)

        mock_col.delete_many.assert_called_once()
        call_filter = mock_col.delete_many.call_args[0][0]
        assert "$in" in call_filter.get("_id", {}), (
            "Rollback delete_many must use $in filter on _id"
        )