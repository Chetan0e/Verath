"""
Tests for non-atomic dead-letter retry producing duplicate
execution and stuck records on partial failure.
"""
import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_dead_doc(task_id="t-1"):
    return {
        "_id": "mongo-oid",
        "task_id": task_id,
        "task_type": "recording",
        "payload": {"file": "/tmp/a.wav"},
        "user_id": "u1",
        "retry_count": 3,
        "max_retries": 3,
        "created_at": datetime.utcnow(),
        "failed_at": datetime.utcnow(),
        "final_error": "timeout",
        "final_stack_trace": "...",
    }


def _queue_instance():
    from app.workers.task_queue import TaskQueue
    q = TaskQueue()
    q._initialized = True
    return q


# ── happy path ────────────────────────────────────────────────────────────────

class TestRetryDeadLetterHappyPath:
    async def test_successful_retry_removes_dead_letter_entry(self, monkeypatch):
        """On success, dead-letter entry must be deleted."""
        dead_doc = _make_dead_doc()
        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(return_value=dead_doc)
        dl_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        main_col = MagicMock()
        main_col.insert_one = AsyncMock(return_value=MagicMock())

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        result = await q.retry_dead_letter_task("t-1")

        assert result is True
        dl_col.delete_one.assert_called_once_with({"task_id": "t-1"})

    async def test_retry_uses_new_task_id(self, monkeypatch):
        """The re-enqueued task must have a different task_id to avoid
        DuplicateKeyError on the unique index."""
        dead_doc = _make_dead_doc("t-orig")
        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(return_value=dead_doc)
        dl_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        inserted_ids = []
        main_col = MagicMock()
        async def capture_insert(doc):
            inserted_ids.append(doc["task_id"])
            return MagicMock()
        main_col.insert_one = capture_insert

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        await q.retry_dead_letter_task("t-orig")

        assert len(inserted_ids) == 1
        assert inserted_ids[0] != "t-orig", "new task must have a fresh task_id"

    async def test_original_task_id_preserved_in_payload(self, monkeypatch):
        """original_task_id must be recorded in the payload for audit."""
        dead_doc = _make_dead_doc("t-orig")
        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(return_value=dead_doc)
        dl_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        inserted_docs = []
        main_col = MagicMock()
        async def capture_insert(doc):
            inserted_docs.append(doc)
            return MagicMock()
        main_col.insert_one = capture_insert

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        await q.retry_dead_letter_task("t-orig")

        payload = inserted_docs[0]["payload"]
        assert payload.get("original_task_id") == "t-orig"


# ── enqueue failure must preserve dead-letter entry ──────────────────────────

class TestRetryDeadLetterEnqueueFailure:
    async def test_dead_letter_preserved_when_enqueue_fails(self, monkeypatch):
        """If enqueue fails, the dead-letter entry must NOT be deleted."""
        dead_doc = _make_dead_doc()
        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(return_value=dead_doc)
        dl_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        main_col = MagicMock()
        main_col.insert_one = AsyncMock(side_effect=Exception("DB error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        result = await q.retry_dead_letter_task("t-1")

        assert result is False
        dl_col.delete_one.assert_not_called()

    async def test_returns_false_when_task_not_in_dead_letter(self, monkeypatch):
        """retry_dead_letter_task must return False when task_id is absent."""
        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": MagicMock(),
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        result = await q.retry_dead_letter_task("nonexistent")
        assert result is False


# ── duplicate retry must not double-execute ───────────────────────────────────

class TestDuplicateRetry:
    async def test_duplicate_retry_does_not_enqueue_twice(self, monkeypatch):
        """Calling retry_dead_letter_task twice with the same task_id must not
        produce two main-queue entries.  The second call finds no dead-letter
        entry (already deleted) and returns False."""
        dead_doc = _make_dead_doc("t-dup")
        find_results = [dead_doc, None]   # first call finds it; second does not

        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(side_effect=find_results)
        dl_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        insert_count = {"n": 0}
        main_col = MagicMock()
        async def counting_insert(doc):
            insert_count["n"] += 1
            return MagicMock()
        main_col.insert_one = counting_insert

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        r1 = await q.retry_dead_letter_task("t-dup")
        r2 = await q.retry_dead_letter_task("t-dup")

        assert r1 is True
        assert r2 is False
        assert insert_count["n"] == 1, "task must only be enqueued once"


# ── _move_to_dead_letter ordering ─────────────────────────────────────────────

class TestMoveToDeadLetterOrdering:
    async def test_main_queue_delete_only_after_dead_letter_insert(self, monkeypatch):
        """_move_to_dead_letter must insert into dead-letter before deleting
        from the main queue."""
        task_doc = {
            "_id": "mongo-oid",
            "task_id": "t-fail",
            "task_type": "recording",
            "payload": {},
            "user_id": "u1",
            "worker_id": "w-1",
            "retry_count": 3,
            "max_retries": 3,
            "created_at": datetime.utcnow(),
        }

        op_order = []

        dl_col = MagicMock()
        async def dl_insert(doc):
            op_order.append("dl_insert")
            return MagicMock()
        dl_col.insert_one = dl_insert

        main_col = MagicMock()
        main_col.find_one = AsyncMock(return_value=task_doc)
        async def main_delete(query):
            op_order.append("main_delete")
            return MagicMock(deleted_count=1)
        main_col.delete_one = main_delete

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        q.worker_id = "w-1"
        await q._move_to_dead_letter("t-fail", "err", "trace")

        assert op_order == ["dl_insert", "main_delete"], \
            "dead-letter insert must happen before main-queue delete"

    async def test_duplicate_dead_letter_insert_still_removes_from_main_queue(self, monkeypatch):
        """If dead-letter insert raises (e.g. task already there from a prior
        crash), the main-queue entry must still be cleaned up."""
        task_doc = {
            "task_id": "t-crash",
            "task_type": "recording",
            "payload": {},
            "user_id": "u1",
            "worker_id": "w-1",
            "retry_count": 3,
            "max_retries": 3,
            "created_at": datetime.utcnow(),
        }

        dl_col = MagicMock()
        dl_col.insert_one = AsyncMock(side_effect=Exception("E11000 duplicate key"))

        main_col = MagicMock()
        main_col.find_one = AsyncMock(return_value=task_doc)
        main_col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        q.worker_id = "w-1"
        await q._move_to_dead_letter("t-crash", "err", "trace")

        main_col.delete_one.assert_called_once_with({"task_id": "t-crash"})


# ── queue consistency regression ──────────────────────────────────────────────

class TestQueueConsistency:
    async def test_queue_consistency_before_and_after_retry(self, monkeypatch):
        """After a successful retry, the task must appear exactly once in the
        main queue and zero times in the dead-letter queue."""
        dead_doc = _make_dead_doc("t-check")

        main_store = {}
        dl_store = {"t-check": dead_doc}

        dl_col = MagicMock()
        dl_col.find_one = AsyncMock(side_effect=lambda q: dl_store.get(q["task_id"]))
        async def dl_delete(q):
            dl_store.pop(q["task_id"], None)
            return MagicMock(deleted_count=1)
        dl_col.delete_one = dl_delete

        main_col = MagicMock()
        async def main_insert(doc):
            main_store[doc["task_id"]] = doc
            return MagicMock()
        main_col.insert_one = main_insert

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=lambda name: {
            "task_queue": main_col,
            "task_queue_dead_letter": dl_col,
        }[name])

        monkeypatch.setattr("app.workers.task_queue.get_db", lambda: mock_db)

        q = _queue_instance()
        result = await q.retry_dead_letter_task("t-check")

        assert result is True
        assert len(main_store) == 1,          "exactly one entry in main queue"
        assert "t-check" not in dl_store,     "dead-letter entry must be gone"
        # The new entry must NOT use the original task_id
        assert "t-check" not in main_store,   "new task_id must differ from original"