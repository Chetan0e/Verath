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

@router.post("/record/upload")
async def upload_record(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    timestamp: Optional[str] = Form(None)
):
    """Process an audio file uploaded from the mobile app."""
    try:
        logger.info(f"Received audio upload from user {user_id}")
        
        # Create a temporary path for the uploaded file
        temp_dir = Path("data/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Enforce a 50MB file size limit — read the entire upload into
        # memory in chunks before writing to disk so oversized files are
        # rejected without filling the disk. shutil.copyfileobj has no
        # size limit and would write gigabytes before any check ran.
        MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
        chunks = []
        total_bytes = 0
        chunk_size = 64 * 1024  # 64 KB read buffer

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum allowed size is "
                           f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                )
            chunks.append(chunk)

        file_ext = Path(file.filename or "").suffix.lower() or ".wav"
        file_path = temp_dir / f"upload_{user_id}_{os.urandom(4).hex()}{file_ext}"

        with open(file_path, "wb") as buffer:
            for chunk in chunks:
                buffer.write(chunk)
            
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
