import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logger = logging.getLogger(__name__)

# ── MongoDB for task tracking + dead-letter ───────────────────────────────────
_mongo = AsyncIOMotorClient(settings.mongo_uri)
_db = _mongo[settings.database_name]
_tasks_col = _db["worker_tasks"]
_dead_letter_col = _db["dead_letter"]


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"  # exhausted all retries


# ── In-memory queue ───────────────────────────────────────────────────────────
_queue: asyncio.Queue = asyncio.Queue()
_worker_running = False


# ── Public: enqueue a job ─────────────────────────────────────────────────────
async def enqueue_task(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    task_name: str = "unnamed",
) -> str:
    """Add a coroutine to the worker queue. Returns a task_id for status polling."""
    task_id = str(uuid.uuid4())
    kwargs = kwargs or {}

    await _tasks_col.insert_one({
        "_id": task_id,
        "name": task_name,
        "status": TaskStatus.PENDING,
        "attempts": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "error": None,
    })

    await _queue.put((task_id, task_name, func, args, kwargs))
    logger.info(f"Enqueued task {task_id} ({task_name})")
    return task_id


# ── Public: check task status ─────────────────────────────────────────────────
async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    doc = await _tasks_col.find_one({"_id": task_id})
    return doc


# ── Internal: run one task with retry ────────────────────────────────────────
async def _run_with_retry(task_id: str, task_name: str, func: Callable, args: tuple, kwargs: dict):
    MAX_ATTEMPTS = 3

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            await _tasks_col.update_one(
                {"_id": task_id},
                {"$set": {
                    "status": TaskStatus.PROCESSING,
                    "attempts": attempt,
                    "updated_at": datetime.utcnow(),
                }}
            )

            # Run the actual coroutine
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

            # Success
            await _tasks_col.update_one(
                {"_id": task_id},
                {"$set": {
                    "status": TaskStatus.COMPLETED,
                    "updated_at": datetime.utcnow(),
                }}
            )
            logger.info(f"Task {task_id} ({task_name}) completed on attempt {attempt}")
            return

        except Exception as e:
            logger.warning(f"Task {task_id} attempt {attempt} failed: {e}")
            if attempt < MAX_ATTEMPTS:
                # Exponential backoff: 2s, 4s, 8s
                await asyncio.sleep(2 ** attempt)
            else:
                # All attempts exhausted → dead letter
                logger.error(f"Task {task_id} ({task_name}) exhausted all retries. Sending to dead letter.")
                await _tasks_col.update_one(
                    {"_id": task_id},
                    {"$set": {
                        "status": TaskStatus.DEAD,
                        "error": str(e),
                        "updated_at": datetime.utcnow(),
                    }}
                )
                await _dead_letter_col.insert_one({
                    "_id": str(uuid.uuid4()),
                    "original_task_id": task_id,
                    "task_name": task_name,
                    "error": str(e),
                    "failed_at": datetime.utcnow(),
                    "args_repr": str(args)[:500],   # truncated for safety
                    "kwargs_repr": str(kwargs)[:500],
                })


# ── Worker loop ───────────────────────────────────────────────────────────────
async def _worker_loop():
    global _worker_running
    _worker_running = True
    logger.info("Background worker started")

    while True:
        try:
            task_id, task_name, func, args, kwargs = await _queue.get()
            await _run_with_retry(task_id, task_name, func, args, kwargs)
            _queue.task_done()
        except asyncio.CancelledError:
            logger.info("Background worker shutting down")
            break
        except Exception as e:
            logger.error(f"Unexpected worker loop error: {e}")


def start_worker():
    """Call this once at app startup (e.g. in main.py lifespan)."""
    asyncio.create_task(_worker_loop())


# ── Background worker class for API compatibility ───────────────────────────────
class BackgroundWorker:
    """Wrapper class for background worker functionality."""

    async def enqueue_recording(self, session, user_id: str) -> str:
        """Enqueue a recording session for processing."""
        from app.services.pipeline import process_audio
        # Create actual processing function
        async def process_recording():
            try:
                from app.services.audio import record_audio
                file_path = record_audio(
                    filename=session.filename,
                    duration=session.duration
                )
                await process_audio(file_path, user_id)
            except Exception as e:
                logger.error(f"Recording processing failed: {e}")
                raise

        return await enqueue_task(
            func=process_recording,
            task_name=f"recording_{session.session_type}",
        )

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return await get_task_status(task_id)

    async def schedule_daily_compression(self, user_id: str) -> str:
        """Schedule daily memory compression."""
        from app.db.memory_lifecycle import memory_lifecycle_manager
        async def compress_memories():
            try:
                await memory_lifecycle_manager.auto_promote_important_memories(user_id)
                await memory_lifecycle_manager.enforce_lifecycle_limits(user_id)
            except Exception as e:
                logger.error(f"Compression failed: {e}")
                raise

        return await enqueue_task(
            func=compress_memories,
            task_name="daily_compression",
        )

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics from MongoDB."""
        try:
            pending = await _tasks_col.count_documents({"status": TaskStatus.PENDING})
            processing = await _tasks_col.count_documents({"status": TaskStatus.PROCESSING})
            completed = await _tasks_col.count_documents({"status": TaskStatus.COMPLETED})
            failed = await _tasks_col.count_documents({"status": TaskStatus.FAILED})
            dead = await _tasks_col.count_documents({"status": TaskStatus.DEAD})
            return {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "dead": dead
            }
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "dead": 0
            }

    async def get_dead_letter_tasks(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks from dead letter queue."""
        try:
            cursor = _dead_letter_col.find().sort("failed_at", -1).limit(limit)
            tasks = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                tasks.append(doc)
            return tasks
        except Exception as e:
            logger.error(f"Error getting dead letter tasks: {e}")
            return []

    async def retry_dead_letter_task(self, task_id: str) -> bool:
        """Retry a task from dead letter queue."""
        try:
            # Find the dead letter entry
            dead_task = await _dead_letter_col.find_one({"_id": task_id})
            if not dead_task:
                return False

            # Re-enqueue the original task
            # Note: In a real implementation, you'd need to reconstruct the original function
            # This is a simplified version that removes from dead letter queue
            await _dead_letter_col.delete_one({"_id": task_id})
            logger.info(f"Task {task_id} removed from dead letter queue for manual retry")
            return True
        except Exception as e:
            logger.error(f"Error retrying dead letter task: {e}")
            return False

    async def cleanup_completed(self, days: int = 7) -> int:
        """Clean up completed tasks older than specified days."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = await _tasks_col.delete_many({
                "status": TaskStatus.COMPLETED,
                "updated_at": {"$lt": cutoff}
            })
            logger.info(f"Cleaned up {result.deleted_count} completed tasks")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up completed tasks: {e}")
            return 0


# Create singleton instance
background_worker = BackgroundWorker()
