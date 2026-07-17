import asyncio
import logging
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.workers.task_queue import (
    Task,
    TaskStatus,
    TaskType,
    task_queue,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Persistent Task Queue Worker
# ============================================================================
#
# task_queue.py is the single orchestration backend: it owns persistence,
# atomic claiming, and retry/dead-letter handling. This module is
# responsible for the two things layered on top of that backend:
#
#   1. Turning public "enqueue a recording / compression job" calls into a
#      structured (task_type, payload) record that task_queue can persist
#      and hand back later — a callable can't survive a process restart, so
#      no closures are stored, only plain data.
#   2. Running the consumer loop that dequeues claimed tasks, dispatches
#      each one to the handler registered for its task_type, and reports
#      the outcome back through task_queue's existing status/retry API.
# ============================================================================

POLL_INTERVAL_SECONDS = 5
BASE_RETRY_DELAY_SECONDS = 30

_consumer_task: Optional[asyncio.Task] = None

# ── Public: enqueue a job ────────────────────────────────────────────────────
async def enqueue_task(
    task_type: TaskType,
    payload: Dict[str, Any],
    user_id: str = "system",
) -> str:
    """
    Enqueue a task on the persistent Mongo-backed queue.

    payload must be JSON/BSON-serializable - it's what gets handed to the
    task_type's registered handler once the consumer loop dequeues the
    task, possibly after a restart, so it has to fully describe the work
    on its own rather than closing over local variables.
    """

    task_id = str(uuid.uuid4())

    task = Task(
        task_id=task_id,
        task_type=task_type,
        payload=payload,
        user_id=user_id,
    )

    success = await task_queue.enqueue(task)

    if not success:
        raise RuntimeError(f"Failed to enqueue task: {task_type.value}")

    logger.info(f"Enqueued persistent task {task_id} ({task_type.value})")

    return task_id


# ── Public: check task status ────────────────────────────────────────────────
async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve task status from the persistent queue backend.
    """

    try:
        return await task_queue.get_task(task_id)
    except Exception as e:
        logger.error(f"Failed to fetch task status for {task_id}: {e}")
        return None


# ── Task dispatch: task_type → handler ───────────────────────────────────────
#
# Handlers take the task's persisted payload and user_id and do the actual
# work. They should let exceptions propagate — _process_task() below is
# what decides whether a failure means a retry or a dead-letter move.
async def _handle_recording_task(payload: Dict[str, Any], user_id: str) -> None:
    """Record and transcribe a session, then store it as a memory."""

    from app.services.audio import record_audio
    from app.services.pipeline import process_audio

    file_path = record_audio(
        filename=payload.get("filename"),
        duration=payload.get("duration"),
    )

    await process_audio(file_path, user_id)

async def _handle_compression_task(payload: Dict[str, Any], user_id: str) -> None:
    """Run daily memory-lifecycle promotion and archival for a user."""

    from app.db.memory_lifecycle import memory_lifecycle_manager

    await memory_lifecycle_manager.auto_promote_important_memories(user_id)
    await memory_lifecycle_manager.enforce_lifecycle_limits(user_id)


TASK_HANDLERS: Dict[TaskType, Callable[[Dict[str, Any], str], Any]] = {
    TaskType.RECORDING: _handle_recording_task,
    TaskType.COMPRESSION: _handle_compression_task,
}


# ── Consumer loop ─────────────────────────────────────────────────────────────
async def _process_task(task: Task) -> None:
    """Run a single claimed task and report the outcome back to task_queue."""

    handler = TASK_HANDLERS.get(task.task_type)

    if handler is None:
        error = f"No handler registered for task type: {task.task_type}"
        logger.error(error)
        await task_queue.mark_for_retry(
            task.task_id,
            error_message=error,
            stack_trace="",
            retry_delay=BASE_RETRY_DELAY_SECONDS,
        )
        return

    try:
        await handler(task.payload, task.user_id)
        await task_queue.update_status(task.task_id, TaskStatus.COMPLETED)
        logger.info(f"Task {task.task_id} ({task.task_type.value}) completed")

    except Exception as e:
        retry_delay = BASE_RETRY_DELAY_SECONDS * (2**task.retry_count)
        logger.error(
            f"Task {task.task_id} ({task.task_type.value}) failed: {e}",
            exc_info=True,
        )
        await task_queue.mark_for_retry(
            task.task_id,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
            retry_delay=retry_delay,
        )


async def _consumer_loop() -> None:
    """
    Continuously poll the persistent queue and execute claimed tasks.

    Runs for the lifetime of the app (started from main.py's lifespan).
    Each iteration dequeues a batch of ready tasks and runs them one at a
    time; it only sleeps when the queue comes back empty, so a backlog
    drains without waiting out the poll interval between every task.
    """

    logger.info("Persistent task queue consumer loop started")

    while True:
        try:
            tasks = await task_queue.dequeue()

            if not tasks:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            for task in tasks:
                await _process_task(task)

        except asyncio.CancelledError:
            logger.info("Persistent task queue consumer loop shutting down")
            raise

        except Exception as e:
            logger.error(f"Unexpected consumer loop error: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def start_worker() -> None:
    """
    Schedule the persistent task queue consumer loop as a background task.

    Called once from the FastAPI lifespan on startup, after the Mongo
    connection is established.
    """

    global _consumer_task
    _consumer_task = asyncio.create_task(_consumer_loop())
    logger.info("Persistent task queue consumer loop scheduled")


async def stop_worker() -> None:
    """Cancel the consumer loop and wait for it to exit, for clean shutdown."""
 
    global _consumer_task

    if _consumer_task is None:
        return

    _consumer_task.cancel()
    try:
        await _consumer_task
    except asyncio.CancelledError:
        pass

    _consumer_task = None
    logger.info("Persistent task queue consumer loop stopped")


# ── Background worker public interface ───────────────────────────────────────
class BackgroundWorker:
    """Public interface for enqueueing and inspecting persistent queue tasks."""

    async def enqueue_recording(
        self,
        session,
        user_id: str,
    ) -> str:
        """Enqueue recording session processing."""

        payload = {
            "filename": session.filename,
            "duration": session.duration,
            "session_type": session.session_type,
        }

        return await enqueue_task(
            task_type=TaskType.RECORDING,
            payload=payload,
            user_id=user_id,
        )

    async def get_task_status(
        self,
        task_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get task status."""

        return await get_task_status(task_id)

    async def schedule_daily_compression(
        self,
        user_id: str,
    ) -> str:
        """Schedule daily memory compression."""

        return await enqueue_task(
            task_type=TaskType.COMPRESSION,
            payload={},
            user_id=user_id,
        )

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Retrieve queue statistics from the persistent queue backend.
        """

        try:
            return await task_queue.get_queue_stats()

        except Exception as e:
            logger.error(
                f"Error getting persistent queue stats: {e}"
            )

            return {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "dead": 0,
            }

    async def get_dead_letter_tasks(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve dead-letter tasks from the persistent queue backend.
        """

        try:
            return await task_queue.get_dead_letter_tasks(
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error getting dead letter tasks: {e}")
            return []

    async def retry_dead_letter_task(
        self,
        task_id: str,
    ) -> bool:
        """
        Retry a dead-letter task using the persistent queue backend.
        """

        try:
            return await task_queue.retry_dead_letter_task(
                task_id
            )

        except Exception as e:
            logger.error(
                f"Error retrying dead letter task: {e}"
            )
            return False

    async def cleanup_completed(
        self,
        days: int = 7,
    ) -> int:
        """
        Deprecated cleanup compatibility method.

        Cleanup behavior should be handled by the persistent
        queue backend lifecycle management.
        """

        logger.info(
            "Legacy cleanup_completed() compatibility "
            "method invoked"
        )

        return 0


# Singleton instance
background_worker = BackgroundWorker()