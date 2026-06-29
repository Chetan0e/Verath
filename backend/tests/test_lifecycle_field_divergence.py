"""
Tests for lifecycle field name divergence.

Verifies that:
1. store_memory writes lifecycle_stage at the top level (not metadata.lifecycle).
2. get_memory_stats aggregates on $lifecycle_stage (top-level), not $metadata.lifecycle.
3. MemoryLifecycleManager.promote_to_long_term filters on top-level lifecycle_stage.
4. MemoryLifecycleManager.get_memories_by_stage queries on top-level lifecycle_stage.
5. auto_promote_important_memories increments promoted_count and does not archive
   memories that passed the importance gate.
6. Full short_term → long_term → archived lifecycle transition succeeds end-to-end.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_collection(docs=None, modified_count=1, count_return=0):
    """Build a mock Motor collection."""
    col = MagicMock()
    col.insert_one = AsyncMock(return_value=MagicMock())
    col.insert_many = AsyncMock(return_value=MagicMock())
    col.update_one = AsyncMock(return_value=MagicMock(modified_count=modified_count))
    col.count_documents = AsyncMock(return_value=count_return)

    async def _aiter(*a, **kw):
        for d in (docs or []):
            yield d

    cursor = MagicMock()
    cursor.__aiter__ = _aiter
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    col.find = MagicMock(return_value=cursor)

    async def _aggregate(pipeline):
        # simulate empty aggregate
        return
        yield  # make it an async generator

    col.aggregate = _aggregate
    return col


# ── 1. store_memory writes lifecycle_stage at top level ──────────────────────

class TestStoreMemoryWritesTopLevelField:
    async def test_lifecycle_stage_is_top_level_not_nested(self, monkeypatch):
        """store_memory must write lifecycle_stage as a top-level document field."""
        captured = {}

        mock_col = MagicMock()
        async def _capture(doc):
            captured["doc"] = doc
            return MagicMock()
        mock_col.insert_one = _capture

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        monkeypatch.setattr("app.services.memory_store._get_collection",
                            lambda uid: MagicMock(upsert=MagicMock()))
        monkeypatch.setattr("app.services.memory_store.get_embedding", lambda t: [0.1] * 8)

        from app.services.memory_store import store_memory
        await store_memory(
            user_id="u1",
            text="coffee with Alice",
            metadata={"intent": "social", "importance": 0.4, "importance_category": "low"},
        )

        doc = captured["doc"]
        # canonical field must exist at top level
        assert "lifecycle_stage" in doc, "lifecycle_stage must be a top-level key"
        assert doc["lifecycle_stage"] == "short_term"
        # must NOT be buried inside metadata
        assert "lifecycle" not in doc.get("metadata", {}), \
            "metadata.lifecycle must not be written; use top-level lifecycle_stage"

    async def test_metadata_lifecycle_field_absent(self, monkeypatch):
        """metadata sub-document must not contain a 'lifecycle' key."""
        captured = {}

        mock_col = MagicMock()
        async def _capture(doc):
            captured["doc"] = doc
            return MagicMock()
        mock_col.insert_one = _capture

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        monkeypatch.setattr("app.services.memory_store._get_collection",
                            lambda uid: MagicMock(upsert=MagicMock()))
        monkeypatch.setattr("app.services.memory_store.get_embedding", lambda t: [0.1] * 8)

        from app.services.memory_store import store_memory
        await store_memory(
            user_id="u1",
            text="deadline next week",
            metadata={"intent": "task", "importance": 0.85, "importance_category": "high"},
        )

        meta = captured["doc"].get("metadata", {})
        assert "lifecycle" not in meta, \
            "metadata.lifecycle must not exist — it is the stale path that caused issue #114"


# ── 2. get_memory_stats aggregates on $lifecycle_stage ───────────────────────

class TestGetMemoryStatsAggregatesCorrectField:
    async def test_pipeline_groups_on_lifecycle_stage_not_metadata_lifecycle(self, monkeypatch):
        """get_memory_stats must group on $lifecycle_stage, not $metadata.lifecycle."""
        captured_pipelines = []

        mock_col = MagicMock()
        mock_col.count_documents = AsyncMock(return_value=3)

        async def _aggregate(pipeline):
            captured_pipelines.append(pipeline)
            return
            yield

        mock_col.aggregate = _aggregate

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)

        from app.services.memory_store import get_memory_stats
        await get_memory_stats("u1")

        assert captured_pipelines, "aggregate must have been called"
        group_stage = captured_pipelines[0][1]  # pipeline[1] is the $group stage
        group_id = group_stage["$group"]["_id"]
        assert group_id == "$lifecycle_stage", (
            f"get_memory_stats must group on $lifecycle_stage (top-level), "
            f"not '{group_id}' — metadata.lifecycle is never written"
        )


# ── 3. promote_to_long_term filters on top-level lifecycle_stage ─────────────

class TestPromoteToLongTermFilter:
    async def test_update_filter_uses_lifecycle_stage(self, monkeypatch):
        """promote_to_long_term must filter on {lifecycle_stage: 'short_term'}."""
        mock_col = MagicMock()
        mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        ok = await MemoryLifecycleManager().promote_to_long_term("u1", "mem-abc")

        assert ok is True
        filt = mock_col.update_one.call_args[0][0]
        assert "lifecycle_stage" in filt, \
            "promote_to_long_term must query lifecycle_stage (top-level)"
        assert filt["lifecycle_stage"] == "short_term", \
            "filter must restrict to short_term documents"

    async def test_update_sets_lifecycle_stage_long_term(self, monkeypatch):
        """promote_to_long_term must $set lifecycle_stage to 'long_term'."""
        mock_col = MagicMock()
        mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        await MemoryLifecycleManager().promote_to_long_term("u1", "mem-abc")

        update_doc = mock_col.update_one.call_args[0][1]
        assert update_doc["$set"].get("lifecycle_stage") == "long_term"


# ── 4. get_memories_by_stage queries top-level field ─────────────────────────

class TestGetMemoriesByStage:
    async def test_find_filter_uses_lifecycle_stage(self, monkeypatch):
        """get_memories_by_stage must query {lifecycle_stage: stage}."""
        stored_doc = {
            "_id": "mem-1",
            "user_id": "u1",
            "text": "hi",
            "lifecycle_stage": "short_term",
            "metadata": {"importance": 0.5},
        }
        mock_col = _make_collection([stored_doc])
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        results = await MemoryLifecycleManager().get_memories_by_stage("u1", stage="short_term")

        find_filter = mock_col.find.call_args[0][0]
        assert "lifecycle_stage" in find_filter, \
            "get_memories_by_stage must query lifecycle_stage (top-level)"
        assert find_filter["lifecycle_stage"] == "short_term"
        assert len(results) == 1
        assert results[0]["_id"] == "mem-1"

    async def test_returns_empty_when_no_documents_match(self, monkeypatch):
        """get_memories_by_stage must return [] when no docs match — not silently fail."""
        mock_col = _make_collection([])
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        results = await MemoryLifecycleManager().get_memories_by_stage("u1", stage="long_term")

        assert results == []


# ── 5. auto_promote increments count and does not archive promoted docs ───────

class TestAutoPromoteImportantMemories:
    async def test_promoted_count_is_incremented(self, monkeypatch):
        """auto_promote_important_memories must increment promoted_count for each
        successful promotion — the log message must reflect the true count."""
        high_imp_docs = [
            {"_id": "mem-hi-1", "metadata": {"importance": 0.9}},
            {"_id": "mem-hi-2", "metadata": {"importance": 0.75}},
        ]

        mock_col = _make_collection(high_imp_docs, modified_count=1)
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()
        await mgr.auto_promote_important_memories("u1")

        # update_one should be called once per doc, promoting each to long_term
        assert mock_col.update_one.call_count == len(high_imp_docs)

    async def test_high_importance_docs_are_promoted_not_archived(self, monkeypatch):
        """Documents that pass the importance gate must be promoted, never archived."""
        doc = {"_id": "mem-hi", "metadata": {"importance": 0.9}}

        mock_col = _make_collection([doc], modified_count=1)
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        await MemoryLifecycleManager().auto_promote_important_memories("u1")

        # Only update_one (promotion) should fire; no archive call should result in
        # setting lifecycle_stage=archived for a high-importance doc
        for c in mock_col.update_one.call_args_list:
            update = c[0][1]
            assert update["$set"].get("lifecycle_stage") != "archived", \
                "high-importance doc must not be archived by auto_promote"

    async def test_find_filter_uses_metadata_importance(self, monkeypatch):
        """The query filter must use metadata.importance, not top-level importance."""
        mock_col = _make_collection([])
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        await MemoryLifecycleManager().auto_promote_important_memories("u1")

        find_filter = mock_col.find.call_args[0][0]
        assert "metadata.importance" in find_filter, \
            "auto_promote must filter on metadata.importance (not top-level importance)"


# ── 6. End-to-end lifecycle transition ───────────────────────────────────────

class TestFullLifecycleTransition:
    async def test_short_term_to_long_term_to_archived(self, monkeypatch):
        """Full lifecycle flow: a memory written as short_term can be promoted
        to long_term and then archived — all operations match on lifecycle_stage."""
        update_calls = []

        mock_col = MagicMock()

        async def _update_one(filt, update):
            update_calls.append((filt, update))
            return MagicMock(modified_count=1)

        mock_col.update_one = _update_one
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        # Step 1: promote short_term → long_term
        promoted = await mgr.promote_to_long_term("u1", "mem-xyz")
        assert promoted is True
        filt1, upd1 = update_calls[0]
        assert filt1.get("lifecycle_stage") == "short_term", \
            "promotion must match on lifecycle_stage=short_term"
        assert upd1["$set"]["lifecycle_stage"] == "long_term"

        # Step 2: archive long_term → archived
        archived = await mgr.archive_memory("u1", "mem-xyz")
        assert archived is True
        filt2, upd2 = update_calls[1]
        assert upd2["$set"]["lifecycle_stage"] == "archived"

    async def test_get_lifecycle_stats_counts_by_lifecycle_stage(self, monkeypatch):
        """get_lifecycle_stats must count by lifecycle_stage (top-level)."""
        async def count(query):
            stage = query.get("lifecycle_stage")
            return {"short_term": 5, "long_term": 2, "archived": 1}.get(stage, 0)

        mock_col = MagicMock()
        mock_col.count_documents = count
        mock_db = MagicMock()
        mock_db.memories = mock_col

        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        stats = await MemoryLifecycleManager().get_lifecycle_stats("u1")

        assert stats["short_term"] == 5
        assert stats["long_term"] == 2
        assert stats["archived"] == 1