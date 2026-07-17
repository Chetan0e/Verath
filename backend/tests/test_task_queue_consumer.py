"""
Tests for the persistent task queue consumer: dispatch by task_type,
completion/retry reporting, and the start_worker/stop_worker lifecycle.

Covers issue #228 — enqueue_task() previously stored only a string preview
of a callable's args and nothing ever called dequeue(), so enqueued tasks
were never executed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workers.task_queue import Task, TaskStatus, TaskType


class TestTaskDispatchRegistry:
    """Every TaskType must resolve to a registered handler."""

    def test_task_handlers_registered_for_every_task_type(self):
        from app.workers.background_worker import TASK_HANDLERS

        assert set(TASK_HANDLERS.keys()) == set(TaskType)


class TestProcessTask:
    """_process_task() dispatches a claimed task and reports the outcome."""

    async def test_successful_handler_marks_task_completed(self, monkeypatch):
        mock_queue_backend = MagicMock()
        mock_queue_backend.update_status = AsyncMock(return_value=True)
        mock_queue_backend.mark_for_retry = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )

        received = {}

        async def fake_handler(payload, user_id):
            received["payload"] = payload
            received["user_id"] = user_id

        monkeypatch.setattr(
            "app.workers.background_worker.TASK_HANDLERS",
            {TaskType.RECORDING: fake_handler},
        )

        from app.workers.background_worker import _process_task

        task = Task(
            task_id="t1",
            task_type=TaskType.RECORDING,
            payload={"filename": "a.wav"},
            user_id="user-9",
        )
        await _process_task(task)

        assert received == {"payload": {"filename": "a.wav"}, "user_id": "user-9"}
        mock_queue_backend.update_status.assert_called_once_with(
            "t1", TaskStatus.COMPLETED
        )
        mock_queue_backend.mark_for_retry.assert_not_called()

    async def test_handler_failure_marks_task_for_retry_with_exponential_backoff(
        self, monkeypatch
    ):
        mock_queue_backend = MagicMock()
        mock_queue_backend.update_status = AsyncMock(return_value=True)
        mock_queue_backend.mark_for_retry = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )

        async def failing_handler(payload, user_id):
            raise ValueError("boom")

        monkeypatch.setattr(
            "app.workers.background_worker.TASK_HANDLERS",
            {TaskType.RECORDING: failing_handler},
        )

        from app.workers.background_worker import _process_task

        # retry_count=2 mirrors a task dequeued after two prior failures.
        task = Task(
            task_id="t2",
            task_type=TaskType.RECORDING,
            payload={},
            user_id="user-9",
            retry_count=2,
        )
        await _process_task(task)

        mock_queue_backend.update_status.assert_not_called()
        mock_queue_backend.mark_for_retry.assert_called_once()

        args, kwargs = mock_queue_backend.mark_for_retry.call_args
        assert args[0] == "t2"
        assert kwargs["error_message"] == "boom"
        assert kwargs["retry_delay"] == 30 * (2**2)  # BASE_RETRY_DELAY_SECONDS * 2^2

    async def test_unregistered_task_type_is_marked_for_retry_not_dropped(
        self, monkeypatch
    ):
        mock_queue_backend = MagicMock()
        mock_queue_backend.mark_for_retry = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )
        monkeypatch.setattr("app.workers.background_worker.TASK_HANDLERS", {})

        from app.workers.background_worker import _process_task

        task = Task(
            task_id="t3", task_type=TaskType.COMPRESSION, payload={}, user_id="user-9"
        )
        await _process_task(task)

        mock_queue_backend.mark_for_retry.assert_called_once()
        assert mock_queue_backend.mark_for_retry.call_args[0][0] == "t3"


class TestConsumerLoop:
    """_consumer_loop() drains dequeue() batches and backs off when empty."""

    async def test_processes_dequeued_batch_in_order(self, monkeypatch):
        monkeypatch.setattr("app.workers.background_worker.POLL_INTERVAL_SECONDS", 0)

        batch = [
            Task(task_id="a", task_type=TaskType.COMPRESSION, payload={}, user_id="u1"),
            Task(task_id="b", task_type=TaskType.COMPRESSION, payload={}, user_id="u2"),
        ]
        calls = {"n": 0}

        async def fake_dequeue(limit=10):
            calls["n"] += 1
            if calls["n"] == 1:
                return batch
            raise asyncio.CancelledError()  # stop the loop deterministically

        mock_queue_backend = MagicMock()
        mock_queue_backend.dequeue = fake_dequeue
        mock_queue_backend.update_status = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )

        processed = []

        async def tracking_handler(payload, user_id):
            processed.append(user_id)

        monkeypatch.setattr(
            "app.workers.background_worker.TASK_HANDLERS",
            {TaskType.COMPRESSION: tracking_handler},
        )

        from app.workers.background_worker import _consumer_loop

        with pytest.raises(asyncio.CancelledError):
            await _consumer_loop()

        assert processed == ["u1", "u2"]

    async def test_empty_queue_backs_off_and_polls_again(self, monkeypatch):
        monkeypatch.setattr("app.workers.background_worker.POLL_INTERVAL_SECONDS", 0)

        calls = {"n": 0}

        async def fake_dequeue(limit=10):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise asyncio.CancelledError()
            return []

        mock_queue_backend = MagicMock()
        mock_queue_backend.dequeue = fake_dequeue
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )

        from app.workers.background_worker import _consumer_loop

        with pytest.raises(asyncio.CancelledError):
            await _consumer_loop()

        assert calls["n"] == 2


class TestWorkerLifecycle:
    """start_worker()/stop_worker() schedule and tear down the loop cleanly."""

    async def test_start_worker_returns_none_and_schedules_a_task(self, monkeypatch):
        mock_queue_backend = MagicMock()
        mock_queue_backend.dequeue = AsyncMock(return_value=[])
        monkeypatch.setattr(
            "app.workers.background_worker.task_queue", mock_queue_backend
        )

        import app.workers.background_worker as bw

        result = bw.start_worker()
        assert result is None
        assert bw._consumer_task is not None
        assert not bw._consumer_task.done()

        await bw.stop_worker()
        assert bw._consumer_task is None

    async def test_stop_worker_is_a_safe_noop_when_never_started(self):
        import app.workers.background_worker as bw

        bw._consumer_task = None  # baseline, independent of test execution order

        await bw.stop_worker()  # must not raise

        assert bw._consumer_task is None


class TestRecordingHandler:
    """_handle_recording_task() must call record_audio then process_audio."""

    async def test_calls_record_audio_then_process_audio_with_payload_fields(
        self, monkeypatch
    ):
        mock_record_audio = MagicMock(return_value="mock_audio_path.wav")
        mock_process_audio = AsyncMock(return_value=None)

        monkeypatch.setattr("app.services.audio.record_audio", mock_record_audio)
        monkeypatch.setattr("app.services.pipeline.process_audio", mock_process_audio)

        from app.workers.background_worker import _handle_recording_task

        await _handle_recording_task(
            {"filename": "lecture.wav", "duration": 45}, "user-5"
        )

        mock_record_audio.assert_called_once_with(filename="lecture.wav", duration=45)
        mock_process_audio.assert_called_once_with("mock_audio_path.wav", "user-5")


class TestCompressionHandler:
    """_handle_compression_task() must promote before enforcing limits."""

    async def test_calls_auto_promote_then_enforce_limits(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.auto_promote_important_memories = AsyncMock(return_value=None)
        mock_manager.enforce_lifecycle_limits = AsyncMock(return_value=None)

        monkeypatch.setattr(
            "app.db.memory_lifecycle.memory_lifecycle_manager", mock_manager
        )

        from app.workers.background_worker import _handle_compression_task

        await _handle_compression_task({}, "user-77")

        mock_manager.auto_promote_important_memories.assert_called_once_with(
            "user-77"
        )
        mock_manager.enforce_lifecycle_limits.assert_called_once_with("user-77")