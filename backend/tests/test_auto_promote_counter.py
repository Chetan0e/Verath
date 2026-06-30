"""
Tests for auto_promote_important_memories counter and observability fix.

Verifies:
  - promoted_count and archived_count are correctly incremented
  - log line is always emitted (not gated on promoted_count > 0)
  - type-mismatched importance values are warned and skipped (not silently archived)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_db(docs):
    """Return a mock db whose memories.find yields docs."""
    async def _iter(*a, **kw):
        for d in docs:
            yield d

    cursor = MagicMock()
    cursor.__aiter__ = _iter
    mock_col = MagicMock()
    mock_col.find = MagicMock(return_value=cursor)
    mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_db = MagicMock()
    mock_db.memories = mock_col
    return mock_db


class TestAutoPromoteCounter:
    async def test_promoted_count_incremented(self, monkeypatch, caplog):
        """promoted_count must reflect the number of promote_to_long_term calls."""
        docs = [
            {"_id": "m1", "metadata": {"importance": 0.9}},
            {"_id": "m2", "metadata": {"importance": 0.7}},
        ]
        mock_db = _make_db(docs)
        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        import logging
        with caplog.at_level(logging.INFO, logger="app.db.memory_lifecycle"):
            await mgr.auto_promote_important_memories("u1")

        assert "promoted=2" in caplog.text
        assert "archived=0" in caplog.text

    async def test_archived_count_incremented(self, monkeypatch, caplog):
        """archived_count must reflect memories that fail the Python-side re-check."""
        # The DB filter already guarantees importance >= 0.6, but we test the
        # archived branch by crafting a doc that slips through the DB mock with
        # a low importance value (simulates a DB mock returning extra docs).
        docs = [
            {"_id": "m3", "metadata": {"importance": 0.3}},
        ]
        mock_db = _make_db(docs)
        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        import logging
        with caplog.at_level(logging.INFO, logger="app.db.memory_lifecycle"):
            await mgr.auto_promote_important_memories("u1")

        assert "archived=1" in caplog.text
        assert "promoted=0" in caplog.text

    async def test_log_always_emitted_when_zero_promotions(self, monkeypatch, caplog):
        """Log line must be emitted even when no memories are promoted."""
        mock_db = _make_db([])
        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        import logging
        with caplog.at_level(logging.INFO, logger="app.db.memory_lifecycle"):
            await mgr.auto_promote_important_memories("u1")

        assert "Auto-promotion complete" in caplog.text

    async def test_type_mismatch_importance_warns_and_skips(self, monkeypatch, caplog):
        """Non-numeric metadata.importance must emit a warning and skip the doc
        without archiving it (no silent data loss)."""
        docs = [
            {"_id": "m4", "metadata": {"importance": "high"}},   # string, not float
        ]
        mock_db = _make_db(docs)
        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        import logging
        with caplog.at_level(logging.WARNING, logger="app.db.memory_lifecycle"):
            await mgr.auto_promote_important_memories("u1")

        # Warning must be emitted
        assert "non-numeric" in caplog.text
        # update_one must NOT have been called (no silent archive)
        mock_db.memories.update_one.assert_not_called()

    async def test_mixed_batch_counts_correctly(self, monkeypatch, caplog):
        """Mixed batch: 2 promoted, 1 archived, 1 type-mismatch skipped."""
        docs = [
            {"_id": "m5", "metadata": {"importance": 0.8}},   # promote
            {"_id": "m6", "metadata": {"importance": 0.65}},  # promote
            {"_id": "m7", "metadata": {"importance": 0.2}},   # archive
            {"_id": "m8", "metadata": {"importance": None}},  # skip (warn)
        ]
        mock_db = _make_db(docs)
        monkeypatch.setattr("app.db.memory_lifecycle.get_db", lambda: mock_db)

        from app.db.memory_lifecycle import MemoryLifecycleManager
        mgr = MemoryLifecycleManager()

        import logging
        with caplog.at_level(logging.WARNING, logger="app.db.memory_lifecycle"):
            await mgr.auto_promote_important_memories("u1")

        assert "promoted=2" in caplog.text
        assert "archived=1" in caplog.text
        assert "non-numeric" in caplog.text
        # update_one called for m5 + m6 (promote) + m7 (archive) = 3 times
        assert mock_db.memories.update_one.call_count == 3