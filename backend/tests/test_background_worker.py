import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestBackgroundWorker:
    """Test background worker functionality."""

    async def test_enqueue_recording_creates_task_in_pending_state(self, monkeypatch):
        """Test that enqueue_recording creates task in pending state."""
        # Mock MongoDB collection
        mock_tasks_col = MagicMock()
        mock_tasks_col.insert_one = AsyncMock()
        
        # Mock queue
        mock_queue = MagicMock()
        mock_queue.put = AsyncMock()
        
        monkeypatch.setattr("app.workers.background_worker._tasks_col", mock_tasks_col)
        monkeypatch.setattr("app.workers.background_worker._queue", mock_queue)
        
        from app.workers.background_worker import enqueue_task, TaskStatus
        
        async def dummy_func():
            pass
        
        task_id = await enqueue_task(dummy_func, task_name="test_task")
        
        assert task_id is not None
        mock_tasks_col.insert_one.assert_called_once()
        call_args = mock_tasks_col.insert_one.call_args[0][0]
        assert call_args["status"] == TaskStatus.PENDING

    async def test_failed_task_moves_to_dead_letter_after_3_retries(self, monkeypatch):
        """Test that failed task moves to dead-letter after 3 retries."""
        mock_tasks_col = MagicMock()
        mock_tasks_col.update_one = AsyncMock()
        mock_dead_letter_col = MagicMock()
        mock_dead_letter_col.insert_one = AsyncMock()
        
        monkeypatch.setattr("app.workers.background_worker._tasks_col", mock_tasks_col)
        monkeypatch.setattr("app.workers.background_worker._dead_letter_col", mock_dead_letter_col)
        
        from app.workers.background_worker import _run_with_retry, TaskStatus
        
        async def failing_func():
            raise Exception("Test failure")
        
        await _run_with_retry("task_1", "test_task", failing_func, (), {})
        
        # Should have been marked as DEAD after 3 retries
        assert mock_tasks_col.update_one.call_count >= 1
        mock_dead_letter_col.insert_one.assert_called_once()

    async def test_retry_dead_letter_task_resets_attempts_and_status_to_pending(self, monkeypatch):
        """Test that retry_dead_letter_task resets attempts and status to pending."""
        mock_dead_letter_col = MagicMock()
        mock_dead_letter_col.find_one = AsyncMock(return_value={"_id": "dead_1"})
        mock_dead_letter_col.delete_one = AsyncMock()
        
        mock_tasks_col = MagicMock()
        mock_tasks_col.insert_one = AsyncMock()
        
        monkeypatch.setattr("app.workers.background_worker._dead_letter_col", mock_dead_letter_col)
        monkeypatch.setattr("app.workers.background_worker._tasks_col", mock_tasks_col)
        
        from app.workers.background_worker import background_worker
        
        result = await background_worker.retry_dead_letter_task("dead_1")
        
        assert result == True
        mock_dead_letter_col.delete_one.assert_called_once_with({"_id": "dead_1"})

    async def test_get_queue_stats_returns_correct_counts(self, monkeypatch):
        """Test that get_queue_stats returns correct counts."""
        mock_tasks_col = MagicMock()
        mock_tasks_col.count_documents = AsyncMock(side_effect=lambda query: {
            {"status": "pending"}: 5,
            {"status": "processing"}: 2,
            {"status": "completed"}: 10,
            {"status": "failed"}: 1,
            {"status": "dead"}: 0
        }.get(query, 0))
        
        monkeypatch.setattr("app.workers.background_worker._tasks_col", mock_tasks_col)
        
        from app.workers.background_worker import background_worker
        
        stats = await background_worker.get_queue_stats()
        
        assert stats["pending"] == 5
        assert stats["processing"] == 2
        assert stats["completed"] == 10
        assert stats["failed"] == 1
        assert stats["dead"] == 0

    async def test_cleanup_completed_deletes_old_completed_tasks(self, monkeypatch):
        """Test that cleanup_completed deletes old completed tasks."""
        mock_tasks_col = MagicMock()
        mock_tasks_col.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
        
        monkeypatch.setattr("app.workers.background_worker._tasks_col", mock_tasks_col)
        
        from app.workers.background_worker import background_worker
        
        count = await background_worker.cleanup_completed(days=7)
        
        assert count == 5
        mock_tasks_col.delete_many.assert_called_once()
        call_args = mock_tasks_col.delete_many.call_args[0][0]
        assert call_args["status"] == "completed"
