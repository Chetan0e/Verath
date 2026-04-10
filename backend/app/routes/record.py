from fastapi import APIRouter, Depends
from app.models.schema import RecordRequest
from app.services.audio import record_audio
from app.services.pipeline import process_audio
from app.services.auth import get_current_user_id

router = APIRouter()

@router.post("/record")
def record(payload: RecordRequest, user_id: str = Depends(get_current_user_id)):
    file_path = record_audio(filename=payload.filename, duration=payload.duration)
    memory = process_audio(file_path, user_id)
    return {"file": file_path, "stored": memory is not None, "memory": memory}
