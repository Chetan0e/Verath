import pytest
from unittest.mock import AsyncMock, MagicMock


class TestQueueMigrationIntegration:
    """Integration-style validation for queue migration behavior."""

    async def test_enqueue_task_delegates_to_persistent_queue(
        self,
        monkeypatch,
    ):
        """
        Ensure enqueue_task delegates orchestration to task_queue.py.
        """

        mock_queue_backend = MagicMock()
        mock_queue_backend.enqueue = AsyncMock(return_value=True)

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import enqueue_task

        from app.workers.task_queue import TaskType

        task_id = await enqueue_task(
            TaskType.COMPRESSION,
            {"note": "integration_test_task"},
            user_id="user-1",
        )

        assert task_id is not None
        mock_queue_backend.enqueue.assert_called_once()

    async def test_queue_stats_use_persistent_backend(
        self,
        monkeypatch,
    ):
        """
        Ensure queue statistics are delegated to persistent backend.
        """

        mock_queue_backend = MagicMock()

        mock_queue_backend.get_queue_stats = AsyncMock(
            return_value={
                "pending": 3,
                "processing": 1,
                "completed": 7,
                "failed": 0,
                "dead": 0,
            }
        )

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import background_worker

        stats = await background_worker.get_queue_stats()

        assert stats["pending"] == 3
        assert stats["processing"] == 1
        assert stats["completed"] == 7

    async def test_retry_dead_letter_delegates_to_persistent_backend(
        self,
        monkeypatch,
    ):
        """
        Ensure dead-letter retries delegate to persistent backend.
        """

        mock_queue_backend = MagicMock()

        mock_queue_backend.retry_dead_letter_task = AsyncMock(
            return_value=True
        )

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import background_worker

        result = await background_worker.retry_dead_letter_task(
            "dead_task_1"
        )

        assert result is True

    async def test_start_worker_schedules_consumer_loop_and_returns_none(
        self,
        monkeypatch,
    ):
        """
        start_worker() must schedule the consumer loop in the background
        and return immediately, without blocking the FastAPI startup path.
        """

        mock_queue_backend = MagicMock()
        mock_queue_backend.dequeue = AsyncMock(return_value=[])

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import start_worker, stop_worker

        result = start_worker()
        assert result is None
        # Clean up the scheduled task so it doesn't keep polling after the test.
        await stop_worker()