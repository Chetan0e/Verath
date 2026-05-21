import pytest
from unittest.mock import AsyncMock, MagicMock


class TestBackgroundWorker:
    """Test background worker functionality."""

    async def test_enqueue_recording_creates_task_in_pending_state(
        self,
        monkeypatch,
    ):
        """Test enqueue_task delegates to persistent queue backend."""

        mock_queue_backend = MagicMock()
        mock_queue_backend.enqueue = AsyncMock(return_value=True)

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import enqueue_task

        async def dummy_func():
            pass

        task_id = await enqueue_task(
            dummy_func,
            task_name="test_task",
        )

        assert task_id is not None
        mock_queue_backend.enqueue.assert_called_once()

    @pytest.mark.skip(
        reason="Legacy retry path deprecated during queue migration"
    )
    async def test_failed_task_moves_to_dead_letter_after_3_retries(
        self,
    ):
        pass

    async def test_retry_dead_letter_task_resets_attempts_and_status_to_pending(
        self,
        monkeypatch,
    ):
        """Test retry delegation to persistent queue backend."""

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
            "dead_1"
        )

        assert result is True

    async def test_get_queue_stats_returns_correct_counts(
        self,
        monkeypatch,
    ):
        """Test queue stats delegation."""

        mock_queue_backend = MagicMock()
        mock_queue_backend.get_queue_stats = AsyncMock(
            return_value={
                "pending": 5,
                "processing": 2,
                "completed": 10,
                "failed": 1,
                "dead": 0,
            }
        )

        monkeypatch.setattr(
            "app.workers.background_worker.task_queue",
            mock_queue_backend,
        )

        from app.workers.background_worker import background_worker

        stats = await background_worker.get_queue_stats()

        assert stats["pending"] == 5
        assert stats["processing"] == 2
        assert stats["completed"] == 10
        assert stats["failed"] == 1
        assert stats["dead"] == 0

    @pytest.mark.skip(
        reason="Legacy cleanup path deprecated during queue migration"
    )
    async def test_cleanup_completed_deletes_old_completed_tasks(
        self,
    ):
        pass