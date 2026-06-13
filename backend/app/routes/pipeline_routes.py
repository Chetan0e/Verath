import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.models.memory import RecordingSession
from app.pipeline.audio_processor import audio_processor
from app.pipeline.extraction_pipeline import extraction_pipeline
from app.pipeline.data_validator import data_validator
from app.workers.background_worker import background_worker
from app.services.auth import get_current_user_id
from app.core.logging_config import logger
from app.core.validators import (
    validate_session_type, validate_duration, validate_task_id,
    validate_limit
)

router = APIRouter()

class RecordingRequest(BaseModel):
    session_type: str = "general"
    duration: int = 10
    filename: Optional[str] = None

class ExtractionRequest(BaseModel):
    text: str

class RetryTaskRequest(BaseModel):
    task_id: str

@router.post("/record/session")
async def record_session(
    request: RecordingRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Record audio with session metadata.
    Session types: manual, lecture, meeting, general, short
    """
    try:
        # Validate input
        validate_session_type(request.session_type)
        validate_duration(request.duration)
        
        session = RecordingSession(
            session_type=request.session_type,
            duration=request.duration,
            filename=request.filename
        )
        
        # Enqueue for background processing
        task_id = await background_worker.enqueue_recording(session, user_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "session_type": session.session_type,
            "message": "Recording queued for processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record session")

@router.post("/extract")
async def extract_memory(
    request: ExtractionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Extract structured memory from text using the hybrid pipeline.
    """
    try:
        # Validate text input
        if not request.text or len(request.text.strip()) < 2:
            raise HTTPException(status_code=400, detail="Text must be at least 2 characters")
        
        if len(request.text) > 10000:
            raise HTTPException(status_code=400, detail="Text exceeds maximum length of 10000 characters")
        
        result = await extraction_pipeline.extract(request.text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to extract memory")

@router.post("/validate")
async def validate_text(
    request: ExtractionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Validate text for noise, length, and duplicates.
    """
    try:
        # Validate text input
        if not request.text or len(request.text.strip()) < 2:
            raise HTTPException(status_code=400, detail="Text must be at least 2 characters")
        
        # Get recent memories for duplicate check
        from app.services.memory_store import all_memories
        recent_memories = await all_memories(user_id, limit=50)
        
        result = await data_validator.validate_memory(request.text, recent_memories)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate text")

@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get status of a background processing task."""
    try:
        validate_task_id(task_id)
        status = await background_worker.get_task_status(task_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get task status")

@router.post("/lifecycle/compress")
async def trigger_compression(
    user_id: str = Depends(get_current_user_id)
):
    """Trigger daily memory compression."""
    try:
        task_id = await background_worker.schedule_daily_compression(user_id)
        return {
            "success": True,
            "task_id": task_id,
            "message": "Compression job scheduled"
        }
    except Exception as e:
        logger.error(f"Error triggering compression: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger compression")

@router.get("/queue/stats")
async def get_queue_stats(user_id: str = Depends(get_current_user_id)):
    """Get queue statistics."""
    try:
        stats = await background_worker.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get queue stats")

@router.get("/queue/dead-letter")
async def get_dead_letter_tasks(
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """Get tasks from dead letter queue."""
    try:
        limit = validate_limit(limit, default=50, max_limit=100)
        tasks = await background_worker.get_dead_letter_tasks(user_id=user_id, limit=limit)
        return {
            "tasks": tasks,
            "count": len(tasks)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dead letter tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get dead letter tasks")

@router.post("/queue/retry")
async def retry_dead_letter_task(
    request: RetryTaskRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Retry a task from dead letter queue."""
    try:
        validate_task_id(request.task_id)
        success = await background_worker.retry_dead_letter_task(request.task_id)
        if success:
            return {
                "success": True,
                "message": f"Task {request.task_id} requeued for processing"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found in dead letter queue")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying dead letter task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retry task")

@router.post("/queue/cleanup")
async def cleanup_completed_tasks(
    days: int = 7,
    user_id: str = Depends(get_current_user_id)
):
    """Clean up completed tasks older than specified days."""
    try:
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="days must be between 1 and 365")
        
        deleted_count = await background_worker.cleanup_completed(days)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} completed tasks"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up completed tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cleanup tasks")
