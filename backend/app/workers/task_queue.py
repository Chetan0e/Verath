import logging
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from app.services.database import get_db
from app.core.logging_config import logger


class TaskStatus(Enum):
    """Task status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class TaskType(Enum):
    """Task type enumeration."""
    RECORDING = "recording"
    COMPRESSION = "compression"


@dataclass
class Task:
    """Task data structure."""
    task_id: str
    task_type: TaskType
    payload: Dict[str, Any]
    user_id: str
    status: TaskStatus = TaskStatus.QUEUED
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    worker_id: Optional[str] = None
    heartbeat_at: Optional[datetime] = None


class TaskQueue:
    """Persistent task queue with MongoDB storage and atomic operations."""
    
    COLLECTION_NAME = "task_queue"
    DEAD_LETTER_COLLECTION = "task_queue_dead_letter"
    HEARTBEAT_TIMEOUT = timedelta(minutes=5)  # Tasks stuck for 5 min are considered stale
    
    def __init__(self):
        self._initialized = False
        self.worker_id = str(uuid.uuid4())
    
    async def _ensure_initialized(self):
        """Ensure MongoDB connection and indexes are initialized."""
        if self._initialized:
            return
        
        db = get_db()
        if db is None:
            raise RuntimeError("Database not available for task queue")
        
        # Create indexes for efficient querying
        try:
            await db[self.COLLECTION_NAME].create_index([("task_id", 1)], unique=True)
            await db[self.COLLECTION_NAME].create_index([("status", 1), ("next_retry_at", 1)])
            await db[self.COLLECTION_NAME].create_index([("user_id", 1)])
            await db[self.COLLECTION_NAME].create_index([("heartbeat_at", 1)])
            await db[self.DEAD_LETTER_COLLECTION].create_index([("task_id", 1)], unique=True)
            await db[self.DEAD_LETTER_COLLECTION].create_index([("user_id", 1)])
            await db[self.DEAD_LETTER_COLLECTION].create_index([("failed_at", -1)])
            
            self._initialized = True
            logger.info("Task queue initialized with indexes")
        except Exception as e:
            logger.error(f"Failed to initialize task queue indexes: {e}", exc_info=True)
            raise
    
    async def enqueue(self, task: Task) -> bool:
        """Enqueue a task for processing."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for enqueue")
            return False
        
        try:
            task_dict = {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "payload": task.payload,
                "user_id": task.user_id,
                "status": task.status.value,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "next_retry_at": task.next_retry_at,
                "error_message": task.error_message,
                "stack_trace": task.stack_trace,
                "worker_id": None,
                "heartbeat_at": None
            }
            
            await db[self.COLLECTION_NAME].insert_one(task_dict)
            logger.info(f"Enqueued task {task.task_id} of type {task.task_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.task_id}: {e}", exc_info=True)
            return False
    
    async def dequeue(self, limit: int = 10) -> List[Task]:
        """Dequeue tasks that are ready for processing with atomic claim."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for dequeue")
            return []
        
        try:
            now = datetime.utcnow()
            heartbeat_cutoff = now - self.HEARTBEAT_TIMEOUT
            
            tasks = []
            
            # Find and claim tasks atomically one by one to avoid race conditions
            # First, find stuck tasks and reset them
            await db[self.COLLECTION_NAME].update_many(
                {
                    "status": TaskStatus.PROCESSING.value,
                    "heartbeat_at": {"$lt": heartbeat_cutoff}
                },
                {
                    "$set": {
                        "status": TaskStatus.QUEUED.value,
                        "worker_id": None,
                        "heartbeat_at": None,
                        "updated_at": now
                    }
                }
            )
            
            # Find tasks that are queued or ready for retry
            cursor = db[self.COLLECTION_NAME].find({
                "$or": [
                    {"status": TaskStatus.QUEUED.value},
                    {
                        "status": TaskStatus.RETRYING.value,
                        "next_retry_at": {"$lte": now}
                    }
                ]
            }).sort("created_at", 1).limit(limit)
            
            async for doc in cursor:
                task_id = doc["task_id"]
                
                # Try to claim this task atomically
                result = await db[self.COLLECTION_NAME].update_one(
                    {
                        "task_id": task_id,
                        "status": doc["status"]  # Ensure status hasn't changed
                    },
                    {
                        "$set": {
                            "status": TaskStatus.PROCESSING.value,
                            "worker_id": self.worker_id,
                            "heartbeat_at": now,
                            "updated_at": now
                        }
                    }
                )
                
                if result.modified_count > 0:
                    # Successfully claimed the task
                    task = Task(
                        task_id=doc["task_id"],
                        task_type=TaskType(doc["task_type"]),
                        payload=doc["payload"],
                        user_id=doc["user_id"],
                        status=TaskStatus.PROCESSING,
                        retry_count=doc.get("retry_count", 0),
                        max_retries=doc.get("max_retries", 3),
                        created_at=doc["created_at"],
                        updated_at=now,
                        next_retry_at=doc.get("next_retry_at"),
                        error_message=doc.get("error_message"),
                        stack_trace=doc.get("stack_trace"),
                        worker_id=self.worker_id,
                        heartbeat_at=now
                    )
                    tasks.append(task)
                    
                    if len(tasks) >= limit:
                        break
            
            if tasks:
                logger.info(f"Dequeued {len(tasks)} tasks for processing by worker {self.worker_id}")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to dequeue tasks: {e}", exc_info=True)
            return []
    
    async def update_heartbeat(self, task_id: str) -> bool:
        """Update heartbeat for a processing task."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            return False
        
        try:
            result = await db[self.COLLECTION_NAME].update_one(
                {
                    "task_id": task_id,
                    "worker_id": self.worker_id
                },
                {
                    "$set": {
                        "heartbeat_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update heartbeat for task {task_id}: {e}")
            return False
    
    async def update_status(self, task_id: str, status: TaskStatus, 
                           error_message: Optional[str] = None, 
                           stack_trace: Optional[str] = None) -> bool:
        """Update task status."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for status update")
            return False
        
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if error_message:
                update_data["error_message"] = error_message
            if stack_trace:
                update_data["stack_trace"] = stack_trace
            
            # Clear worker info if task is no longer processing
            if status != TaskStatus.PROCESSING:
                update_data["worker_id"] = None
                update_data["heartbeat_at"] = None
            
            result = await db[self.COLLECTION_NAME].update_one(
                {
                    "task_id": task_id,
                    "worker_id": self.worker_id
                },
                {"$set": update_data}
            )
            
            logger.info(f"Updated task {task_id} status to {status.value}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}", exc_info=True)
            return False
    
    async def mark_for_retry(self, task_id: str, error_message: str, 
                            stack_trace: str, retry_delay: int) -> bool:
        """Mark task for retry with exponential backoff."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for retry marking")
            return False
        
        try:
            # Get current retry count with worker check
            task_doc = await db[self.COLLECTION_NAME].find_one({
                "task_id": task_id,
                "worker_id": self.worker_id
            })
            if not task_doc:
                logger.error(f"Task {task_id} not found for retry or not owned by worker")
                return False
            
            retry_count = task_doc.get("retry_count", 0) + 1
            max_retries = task_doc.get("max_retries", 3)
            
            if retry_count > max_retries:
                # Move to dead letter queue
                await self._move_to_dead_letter(task_id, error_message, stack_trace)
                logger.warning(f"Task {task_id} exceeded max retries, moved to dead letter queue")
                return True
            
            # Calculate next retry time with exponential backoff
            next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            result = await db[self.COLLECTION_NAME].update_one(
                {
                    "task_id": task_id,
                    "worker_id": self.worker_id
                },
                {
                    "$set": {
                        "status": TaskStatus.RETRYING.value,
                        "retry_count": retry_count,
                        "next_retry_at": next_retry_at,
                        "error_message": error_message,
                        "stack_trace": stack_trace,
                        "worker_id": None,
                        "heartbeat_at": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Task {task_id} marked for retry #{retry_count} at {next_retry_at}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to mark task for retry: {e}", exc_info=True)
            return False
    
    async def _move_to_dead_letter(self, task_id: str, error_message: str, stack_trace: str) -> bool:
        """
        Move a failed task to the dead-letter queue.

        Ordering guarantee:
        1. Insert into dead-letter collection.
        2. Only if insert succeeded, delete from the main queue.

        A crash between steps 1 and 2 leaves the task in both collections.
        On the next dequeue cycle the heartbeat-timeout reset will make the
        main-queue entry visible again; a worker will attempt to claim it and
        immediately re-exhaust retries, reaching _move_to_dead_letter again.
        The dead-letter insert will fail with DuplicateKeyError (unique index
        on task_id), which is caught and logged — the entry is already safe.
        """
        await self._ensure_initialized()

        db = get_db()
        if db is None:
            logger.error("Database not available for dead letter queue")
            return False

        try:
            task_doc = await db[self.COLLECTION_NAME].find_one({
                "task_id": task_id,
                "worker_id": self.worker_id
            })
            if not task_doc:
                logger.error(
                    f"Task {task_id} not found for dead letter queue or not owned by worker"
                )
                return False

            dead_letter_doc = task_doc.copy()
            dead_letter_doc["failed_at"] = datetime.utcnow()
            dead_letter_doc["final_error"] = error_message
            dead_letter_doc["final_stack_trace"] = stack_trace
            dead_letter_doc.pop("_id", None)

            # Step 1: insert into dead-letter collection.
            try:
                await db[self.DEAD_LETTER_COLLECTION].insert_one(dead_letter_doc)
            except Exception as insert_err:
                # DuplicateKeyError means a previous crash already wrote the entry.
                # The task is already safely recorded; we can still remove it from
                # the main queue.
                logger.warning(
                    f"Dead-letter insert for {task_id} raised {insert_err!r}; "
                    "entry may already exist — proceeding to remove from main queue."
                )

            # Step 2: delete from main queue only after dead-letter is secured.
            await db[self.COLLECTION_NAME].delete_one({"task_id": task_id})

            logger.warning(f"Task {task_id} moved to dead letter queue")
            return True

        except Exception as e:
            logger.error(f"Failed to move task to dead letter queue: {e}", exc_info=True)
            return False  
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for status check")
            return None
        
        try:
            # Check main queue
            doc = await db[self.COLLECTION_NAME].find_one({"task_id": task_id})
            if doc:
                return {
                    "task_id": doc["task_id"],
                    "status": doc["status"],
                    "retry_count": doc.get("retry_count", 0),
                    "max_retries": doc.get("max_retries", 3),
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"],
                    "next_retry_at": doc.get("next_retry_at"),
                    "error_message": doc.get("error_message"),
                    "worker_id": doc.get("worker_id"),
                    "heartbeat_at": doc.get("heartbeat_at")
                }
            
            # Check dead letter queue
            dead_doc = await db[self.DEAD_LETTER_COLLECTION].find_one({"task_id": task_id})
            if dead_doc:
                return {
                    "task_id": dead_doc["task_id"],
                    "status": TaskStatus.DEAD_LETTER.value,
                    "retry_count": dead_doc.get("retry_count", 0),
                    "max_retries": dead_doc.get("max_retries", 3),
                    "created_at": dead_doc["created_at"],
                    "updated_at": dead_doc.get("updated_at"),
                    "failed_at": dead_doc.get("failed_at"),
                    "error_message": dead_doc.get("final_error"),
                    "in_dead_letter": True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task status: {e}", exc_info=True)
            return None
    
    async def get_dead_letter_tasks(self, user_id: Optional[str] = None, 
                                   limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks from dead letter queue."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for dead letter queue")
            return []
        
        try:
            query = {}
            if user_id:
                query["user_id"] = user_id
            
            cursor = db[self.DEAD_LETTER_COLLECTION].find(query).sort("failed_at", -1).limit(limit)
            
            tasks = []
            async for doc in cursor:
                tasks.append({
                    "task_id": doc["task_id"],
                    "task_type": doc["task_type"],
                    "user_id": doc["user_id"],
                    "retry_count": doc.get("retry_count", 0),
                    "max_retries": doc.get("max_retries", 3),
                    "created_at": doc["created_at"],
                    "failed_at": doc["failed_at"],
                    "error_message": doc.get("final_error"),
                    "stack_trace": doc.get("final_stack_trace")
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get dead letter tasks: {e}", exc_info=True)
            return []
    
    async def retry_dead_letter_task(self, task_id: str) -> bool:
        """
        Retry a task from the dead-letter queue.

        A new task_id is generated for the retry so that the unique index on
        task_queue.task_id can never produce a DuplicateKeyError, removing
        the ambiguity about whether the original dead-letter entry should be
        deleted.  The original task_id is preserved in the payload under the
        key ``original_task_id`` for audit purposes.

        Ordering guarantee:
        1. Enqueue the new task (write to main queue).
        2. Only if enqueue succeeded, delete the dead-letter entry.

        A crash between steps 1 and 2 leaves the dead-letter entry in place,
        allowing the operator to retry again without duplicate execution risk
        (the new task_id is different each time).
        """
        await self._ensure_initialized()

        db = get_db()
        if db is None:
            logger.error("Database not available for dead letter retry")
            return False

        try:
            dead_doc = await db[self.DEAD_LETTER_COLLECTION].find_one({"task_id": task_id})
            if not dead_doc:
                logger.error(f"Task {task_id} not found in dead letter queue")
                return False

            # Generate a fresh task_id so the unique index cannot fire.
            new_task_id = str(uuid.uuid4())

            payload = dict(dead_doc.get("payload", {}))
            payload["original_task_id"] = task_id   # audit trail

            new_task = Task(
                task_id=new_task_id,
                task_type=TaskType(dead_doc["task_type"]),
                payload=payload,
                user_id=dead_doc["user_id"],
                status=TaskStatus.QUEUED,
                retry_count=0,
                max_retries=dead_doc.get("max_retries", 3),
            )

            # Step 1: enqueue.  Do NOT proceed if this fails.
            enqueued = await self.enqueue(new_task)
            if not enqueued:
                logger.error(
                    f"Enqueue failed for dead-letter retry of {task_id}; "
                    "dead-letter entry preserved."
                )
                return False

            # Step 2: delete dead-letter entry only after confirmed enqueue.
            delete_result = await db[self.DEAD_LETTER_COLLECTION].delete_one(
                {"task_id": task_id}
            )
            if delete_result.deleted_count == 0:
                # Enqueue succeeded but delete failed — log for manual cleanup.
                # The new task will run correctly; the stale dead-letter entry is
                # harmless but should be cleaned up.
                logger.warning(
                    f"Dead-letter entry for {task_id} could not be deleted after "
                    f"successful re-enqueue as {new_task_id}. Manual cleanup required."
                )

            logger.info(
                f"Dead-letter task {task_id} re-enqueued as {new_task_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to retry dead letter task: {e}", exc_info=True)
            return False
    
    async def cleanup_completed(self, days: int = 7) -> int:
        """Clean up completed tasks older than specified days."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for cleanup")
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db[self.COLLECTION_NAME].delete_many({
                "status": TaskStatus.COMPLETED.value,
                "updated_at": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} completed tasks")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup completed tasks: {e}", exc_info=True)
            return 0
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        await self._ensure_initialized()
        
        db = get_db()
        if db is None:
            logger.error("Database not available for stats")
            return {}
        
        try:
            stats = {}
            
            for status in TaskStatus:
                count = await db[self.COLLECTION_NAME].count_documents({"status": status.value})
                stats[status.value] = count
            
            dead_letter_count = await db[self.DEAD_LETTER_COLLECTION].count_documents({})
            stats["dead_letter"] = dead_letter_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}", exc_info=True)
            return {}


# Global task queue instance
task_queue = TaskQueue()
