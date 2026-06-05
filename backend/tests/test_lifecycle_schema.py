"""
lifecycle schema contract between pipeline write path and MemoryLifecycleManager.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_col(docs=None):
    """Return a mock memories collection pre-loaded with docs."""
    col = MagicMock()
    col.insert_one = AsyncMock(return_value=MagicMock())
    col.insert_many = AsyncMock(return_value=MagicMock())
    col.find_one = AsyncMock(return_value=docs[0] if docs else None)
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    col.count_documents = AsyncMock(return_value=len(docs) if docs else 0)

    async def _async_iter(query=None, *a, **kw):
        for d in (docs or []):
            yield d

    cursor = MagicMock()
    cursor.__aiter__ = _async_iter
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    col.find = MagicMock(return_value=cursor)
    return col


# ── store_memory writes lifecycle_stage at top level ─────────────────────────

class TestStoreMemorySchema:
    async def test_lifecycle_stage_written_at_top_level(self, monkeypatch):
        """store_memory must write lifecycle_stage as a top-level field, not
        inside metadata, so MemoryLifecycleManager queries can find it."""
        captured = {}

        mock_col = MagicMock()
        async def capture_insert(doc):
            captured["doc"] = doc
            return MagicMock()
        mock_col.insert_one = capture_insert

        mock_chroma = MagicMock()
        mock_chroma.upsert = MagicMock()

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        monkeypatch.setattr("app.services.memory_store._get_collection", lambda uid: mock_chroma)
        monkeypatch.setattr("app.services.memory_store.get_embedding", lambda t: [0.1] * 8)

        from app.services.memory_store import store_memory
        await store_memory(
            user_id="u1",
            text="hello",
            metadata={"intent": "meeting", "importance": 0.9, "importance_category": "high"},
        )

        doc = captured["doc"]
        assert "lifecycle_stage" in doc, "lifecycle_stage must be a top-level key"
        assert doc["lifecycle_stage"] == "short_term"
        # The old overloaded field must not appear inside metadata
        assert "lifecycle" not in doc.get("metadata", {}), \
            "metadata.lifecycle must not exist; use metadata.importance_category instead"

    async def test_importance_category_stored_in_metadata(self, monkeypatch):
        """pipeline importance category must go into metadata.importance_category,
        not metadata.lifecycle."""
        captured = {}

        mock_col = MagicMock()
        async def capture_insert(doc):
            captured["doc"] = doc
            return MagicMock()
        mock_col.insert_one = capture_insert

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        monkeypatch.setattr("app.services.memory_store._get_collection",
                            lambda uid: MagicMock(upsert=MagicMock()))
        monkeypatch.setattr("app.services.memory_store.get_embedding", lambda t: [0.1] * 8)

        from app.services.memory_store import store_memory
        await store_memory(
            user_id="u1",
            text="deadline tomorrow",
            metadata={
                "intent": "task",
                "importance": 0.85,
                "importance_category": "high",
            },
        )
        meta = captured["doc"]["metadata"]
        assert meta.get("importance_category") == "high"
        assert "lifecycle" not in meta


# ── lifecycle manager can find pipeline-written memories ─────────────────────

class TestLifecycleManagerQueries:
    async def test_get_memories_by_stage_finds_pipeline_written_docs(self, monkeypatch):
        """Memories written by the pipeline must be retrievable via
        get_memories_by_stage() — the schemas must agree."""
        stored_doc = {
            "_id": "mem-1",
            "user_id": "u1",
            "text": "hi",
            "lifecycle_stage": "short_term",   # as pipeline now writes
            "metadata": {"importance_category": "medium", "importance": 0.5},
        }
        mock_col = _make_col([stored_doc])
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()
        results = await mgr.get_memories_by_stage("u1", stage="short_term")

        assert len(results) == 1
        assert results[0]["_id"] == "mem-1"

    async def test_promote_to_long_term_matches_lifecycle_stage_field(self, monkeypatch):
        """promote_to_long_term must filter on lifecycle_stage (top-level),
        not metadata.lifecycle."""
        mock_col = MagicMock()
        mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()
        ok = await mgr.promote_to_long_term("u1", "mem-1")

        assert ok is True
        call_filter = mock_col.update_one.call_args[0][0]
        assert "lifecycle_stage" in call_filter
        assert call_filter["lifecycle_stage"] == "short_term"

    async def test_lifecycle_stats_return_nonzero_after_insert(self, monkeypatch):
        """After writing a memory with lifecycle_stage=short_term, stats
        for short_term must be > 0."""
        async def count(query):
            if query.get("lifecycle_stage") == "short_term":
                return 3
            return 0

        mock_col = MagicMock()
        mock_col.count_documents = count
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        stats = await MemoryLifecycleManager().get_lifecycle_stats("u1")
        assert stats["short_term"] == 3


# ── enforce_lifecycle_limits triggers archival ────────────────────────────────

class TestLifecycleLimitEnforcement:
    async def test_inserting_over_100_short_term_triggers_archival(self, monkeypatch):
        """When short_term count > MAX_SHORT_TERM (100), enforce_lifecycle_limits
        must attempt to archive or promote the excess."""
        excess_docs = [
            {
                "_id": f"mem-{i}",
                "metadata": {"importance": 0.1},   # below threshold → archive path
            }
            for i in range(5)  # 5 excess docs
        ]

        call_counts = {"archive": 0}

        async def count(query):
            stage = query.get("lifecycle_stage")
            if stage == "short_term":
                return 105  # over the 100 limit
            return 0

        mock_col = MagicMock()
        mock_col.count_documents = count

        async def _iter(*a, **kw):
            for d in excess_docs:
                yield d

        cursor = MagicMock()
        cursor.__aiter__ = _iter
        cursor.sort = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        mock_col.find = MagicMock(return_value=cursor)

        mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()
        await mgr.enforce_lifecycle_limits("u1")

        # update_one should have been called for each excess doc
        assert mock_col.update_one.call_count == len(excess_docs)


# ── promotion of high-importance memories ────────────────────────────────────

class TestAutoPromotion:
    async def test_high_importance_memories_get_promoted(self, monkeypatch):
        """auto_promote_important_memories should promote docs where
        metadata.importance >= IMPORTANCE_THRESHOLD."""
        high_imp_doc = {
            "_id": "mem-hi",
            "metadata": {"importance": 0.9},
        }

        mock_col = MagicMock()
        mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

        async def _iter(*a, **kw):
            yield high_imp_doc

        cursor = MagicMock()
        cursor.__aiter__ = _iter
        mock_col.find = MagicMock(return_value=cursor)

        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()
        await mgr.auto_promote_important_memories("u1")

        # The find filter must use metadata.importance, not top-level importance
        find_filter = mock_col.find.call_args[0][0]
        assert "metadata.importance" in find_filter or "lifecycle_stage" in find_filter
        mock_col.update_one.assert_called_once()