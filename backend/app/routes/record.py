from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
import os
import shutil
from pathlib import Path
from app.models.schema import RecordRequest
from app.services.audio import record_audio
from app.services.pipeline import process_audio
from app.services.auth import get_current_user_id
from app.core.exceptions import TranscriptionError, MemoryStorageError
from app.core.logging_config import logger

router = APIRouter()

@router.post("/record")
async def record(payload: RecordRequest, user_id: str = Depends(get_current_user_id)):
    """Record audio and process it through the intelligent extraction pipeline."""
    try:
        logger.info(f"Recording audio for user {user_id}")
        file_path = record_audio(filename=payload.filename, duration=payload.duration)
        memory = await process_audio(file_path, user_id)
        
        return {
            "success": memory is not None,
            "memory": memory,
            "message": "Audio processed successfully" if memory else "Processing failed (Transcription too short or no signal)",
            "error": None if memory else "Low signal or no speech detected"
        }
    except TranscriptionError as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except MemoryStorageError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in record: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")

ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/x-flac",
    "audio/aac",
    "audio/x-m4a",
}

ALLOWED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".mp4", ".webm", ".ogg", ".flac", ".aac", ".m4a"
}


@router.post("/record/upload")
async def upload_record(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    timestamp: Optional[str] = Form(None)
):
    """Process an audio file uploaded from the mobile app."""
    try:
        logger.info(f"Received audio upload from user {user_id}")

        # Validate MIME type — reject non-audio files before writing to disk
        content_type = (file.content_type or "").lower().split(";")[0].strip()
        if content_type not in ALLOWED_AUDIO_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '{content_type}'. "
                       f"Allowed types: {', '.join(sorted(ALLOWED_AUDIO_MIME_TYPES))}",
            )

        # Validate file extension as a second layer of defence
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file extension '{file_ext}'. "
                       f"Allowed extensions: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            )

        # Create a temporary path for the uploaded file
        temp_dir = Path("data/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = temp_dir / f"upload_{user_id}_{os.urandom(4).hex()}.wav"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process the saved file, timestamp
        memory = await process_audio(str(file_path), user_id, timestamp=timestamp)
        
        return {
            "success": memory is not None,
            "memory": memory,
            "message": "Audio processed successfully" if memory else "Processing failed (Transcription too short or no signal)",
            "error": None if memory else "Low signal or no speech detected"
        }
    except Exception as e:
        logger.error(f"Error processing uploaded audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")
    finally:
        # Ensure file is removed if it still exists
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
