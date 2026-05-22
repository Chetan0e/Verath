import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.config import settings
from app.workers.task_queue import (
    Task,
    TaskType,
    task_queue,
)

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


# Legacy → persistent queue state mapping used during migration.
LEGACY_TO_PERSISTENT_STATUS = {
    "PENDING": "QUEUED",
    "PROCESSING": "PROCESSING",
    "COMPLETED": "COMPLETED",
    "FAILED": "FAILED",
    "DEAD": "DEAD_LETTER",
}


# ============================================================================
# Queue Migration Strategy
# ============================================================================
#
# Phase 1 (current):
# - Preserve legacy background_worker interfaces
# - Delegate orchestration behavior to task_queue.py
# - Maintain backward compatibility for existing imports/routes
#
# Phase 2:
# - Align task status semantics between legacy and persistent queues
# - Remove duplicated retry/dead-letter orchestration paths
#
# Phase 3:
# - Fully remove deprecated in-memory queue implementation
# - Use task_queue.py as the single orchestration backend
#
# NOTE:
# The in-memory queue remains temporarily as a compatibility layer during the
# staged migration toward persistent queue orchestration.
# ============================================================================

# Deprecated legacy in-memory queue retained temporarily for compatibility.
_queue: asyncio.Queue = asyncio.Queue()

_worker_running = False


# ── Public: enqueue a job ────────────────────────────────────────────────────
async def enqueue_task(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    task_name: str = "unnamed",
) -> str:
    """
    Enqueue a task using the persistent Mongo-backed queue backend.

    This preserves the existing background worker interface while
    delegating orchestration behavior to task_queue.py.
    """

    task_id = str(uuid.uuid4())
    kwargs = kwargs or {}

    # Infer task type
    if "record" in task_name.lower():
        task_type = TaskType.RECORDING
    else:
        task_type = TaskType.COMPRESSION

    task = Task(
        task_id=task_id,
        task_type=task_type,
        payload={
            "task_name": task_name,
            "args_repr": str(args)[:500],
            "kwargs_repr": str(kwargs)[:500],
        },
        user_id="system",
    )

    success = await task_queue.enqueue(task)

    if not success:
        raise RuntimeError(f"Failed to enqueue task: {task_name}")

    logger.info(f"Enqueued persistent task {task_id} ({task_name})")

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


# ── Legacy retry compatibility layer ─────────────────────────────────────────
#
# NOTE:
# Legacy retry/dead-letter orchestration paths are retained temporarily
# during staged migration toward the persistent task queue backend.
#
# New task orchestration should use task_queue.py directly.
#
async def _run_with_retry(
    task_id: str,
    task_name: str,
    func: Callable,
    args: tuple,
    kwargs: dict,
):
    """
    Deprecated compatibility wrapper retained during migration.

    The persistent queue backend should handle retry orchestration.
    """

    try:
        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: func(*args, **kwargs),
            )

        logger.info(
            f"Legacy compatibility task completed: "
            f"{task_id} ({task_name})"
        )

    except Exception as e:
        logger.error(
            f"Legacy compatibility retry path failed "
            f"for {task_id}: {e}"
        )
        raise


# ── Worker loop ──────────────────────────────────────────────────────────────
#
# NOTE:
# Deprecated legacy worker loop retained temporarily for backward
# compatibility. Active orchestration has been migrated toward
# task_queue.py.
#
# This loop should no longer receive newly enqueued tasks.
#
async def _worker_loop():
    global _worker_running

    _worker_running = True

    logger.info("Legacy background worker loop started")

    while True:
        try:
            task_id, task_name, func, args, kwargs = await _queue.get()

            await _run_with_retry(
                task_id,
                task_name,
                func,
                args,
                kwargs,
            )

            _queue.task_done()

        except asyncio.CancelledError:
            logger.info("Legacy background worker shutting down")
            break

        except Exception as e:
            logger.error(f"Unexpected worker loop error: {e}")


def start_worker():
    """
    Backward-compatible startup hook.

    Legacy in-memory orchestration has been deprecated in favor
    of the persistent Mongo-backed queue implementation in
    task_queue.py.

    This compatibility layer intentionally preserves the existing
    public worker interface while migration occurs incrementally.
    """

    logger.info(
        "Legacy background worker startup skipped "
        "(persistent task queue is now primary)"
    )


# ── Background worker compatibility wrapper ──────────────────────────────────
class BackgroundWorker:
    """Compatibility wrapper for background worker functionality."""

    async def enqueue_recording(
        self,
        session,
        user_id: str,
    ) -> str:
        """Enqueue recording session processing."""

        from app.services.pipeline import process_audio

        async def process_recording():
            try:
                from app.services.audio import record_audio

                file_path = record_audio(
                    filename=session.filename,
                    duration=session.duration,
                )

                await process_audio(file_path, user_id)

            except Exception as e:
                logger.error(f"Recording processing failed: {e}")
                raise

        return await enqueue_task(
            func=process_recording,
            task_name=f"recording_{session.session_type}",
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

        from app.db.memory_lifecycle import memory_lifecycle_manager

        async def compress_memories():
            try:
                await memory_lifecycle_manager.auto_promote_important_memories(
                    user_id
                )

                await memory_lifecycle_manager.enforce_lifecycle_limits(
                    user_id
                )

            except Exception as e:
                logger.error(f"Compression failed: {e}")
                raise

        return await enqueue_task(
            func=compress_memories,
            task_name="daily_compression",
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