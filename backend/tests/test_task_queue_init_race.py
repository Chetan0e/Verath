"""
Tests for TaskQueue._ensure_initialized concurrency safety.

Verifies that concurrent coroutines calling _ensure_initialized() at startup
result in index creation being executed exactly once per index, with no
RuntimeError propagated to callers.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


@pytest.fixture
def mock_db():
    """Return a mock DB whose create_index records calls with a small delay."""
    db = MagicMock()
    collection = MagicMock()

    async def slow_create_index(*args, **kwargs):
        await asyncio.sleep(0)   # yield — forces cooperative interleaving
        return "index_name"

    collection.create_index = AsyncMock(side_effect=slow_create_index)
    db.__getitem__ = MagicMock(return_value=collection)
    return db, collection


@pytest.fixture
def task_queue_fresh():
    """Return an uninitialised TaskQueue with no module-level side effects."""
    from app.workers.task_queue import TaskQueue
    return TaskQueue()


class TestEnsureInitializedConcurrency:
    """_ensure_initialized must be safe under concurrent async callers."""

    async def test_create_index_called_once_per_index_under_concurrent_callers(
        self, task_queue_fresh, mock_db
    ):
        """10 concurrent callers must trigger create_index exactly 7 times total."""
        db, collection = mock_db

        with patch("app.workers.task_queue.get_db", return_value=db):
            await asyncio.gather(
                *[task_queue_fresh._ensure_initialized() for _ in range(10)]
            )

        # 4 indexes on COLLECTION_NAME + 3 on DEAD_LETTER_COLLECTION = 7 total
        assert collection.create_index.call_count == 7

    async def test_initialized_flag_is_true_after_concurrent_callers(
        self, task_queue_fresh, mock_db
    ):
        """_initialized must be True once all concurrent callers finish."""
        db, _ = mock_db

        with patch("app.workers.task_queue.get_db", return_value=db):
            await asyncio.gather(
                *[task_queue_fresh._ensure_initialized() for _ in range(10)]
            )

        assert task_queue_fresh._initialized is True

    async def test_no_runtime_error_raised_under_concurrent_callers(
        self, task_queue_fresh, mock_db
    ):
        """No RuntimeError must propagate from concurrent _ensure_initialized calls."""
        db, _ = mock_db

        with patch("app.workers.task_queue.get_db", return_value=db):
            results = await asyncio.gather(
                *[task_queue_fresh._ensure_initialized() for _ in range(10)],
                return_exceptions=True,
            )

        errors = [r for r in results if isinstance(r, Exception)]
        assert errors == [], f"Unexpected exceptions: {errors}"

    async def test_second_call_is_noop_after_initialization(
        self, task_queue_fresh, mock_db
    ):
        """Subsequent calls after successful init must not invoke create_index again."""
        db, collection = mock_db

        with patch("app.workers.task_queue.get_db", return_value=db):
            await task_queue_fresh._ensure_initialized()
            first_call_count = collection.create_index.call_count

            await task_queue_fresh._ensure_initialized()
            await task_queue_fresh._ensure_initialized()

        assert collection.create_index.call_count == first_call_count

    async def test_raises_runtime_error_when_db_unavailable(self, task_queue_fresh):
        """RuntimeError must propagate when get_db() returns None."""
        with patch("app.workers.task_queue.get_db", return_value=None):
            with pytest.raises(RuntimeError, match="Database not available"):
                await task_queue_fresh._ensure_initialized()

    async def test_initialized_remains_false_on_index_creation_failure(
        self, task_queue_fresh
    ):
        """_initialized must stay False if index creation raises — no silent half-init."""
        db = MagicMock()
        collection = MagicMock()
        collection.create_index = AsyncMock(side_effect=Exception("mongo error"))
        db.__getitem__ = MagicMock(return_value=collection)

        with patch("app.workers.task_queue.get_db", return_value=db):
            with pytest.raises(Exception, match="mongo error"):
                await task_queue_fresh._ensure_initialized()

        assert task_queue_fresh._initialized is False

    async def test_enqueue_triggers_initialization_exactly_once(
        self, task_queue_fresh, mock_db
    ):
        """Concurrent enqueue() calls at startup must initialise the queue only once."""
        from app.workers.task_queue import Task, TaskType, TaskStatus
        import uuid

        db, collection = mock_db

        # Make insert_one a no-op so enqueue() doesn't fail after init
        collection.insert_one = AsyncMock(return_value=MagicMock())

        def make_task():
            return Task(
                task_id=str(uuid.uuid4()),
                task_type=TaskType.RECORDING,
                payload={},
                user_id="user-1",
            )

        with patch("app.workers.task_queue.get_db", return_value=db):
            await asyncio.gather(*[task_queue_fresh.enqueue(make_task()) for _ in range(10)])

        assert collection.create_index.call_count == 7