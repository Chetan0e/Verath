from fastapi import APIRouter

from app.models.schema import VoiceTrainRequest
from app.services.embedding import get_embedding
from app.services.speaker_training import add_voice, get_voice_profiles

router = APIRouter()


@router.post("/train")
def train_voice(payload: VoiceTrainRequest):
    sample = payload.sample_text or payload.name
    embedding = get_embedding(sample)
    add_voice(payload.name, embedding)
    return {"msg": "voice profile saved", "name": payload.name}


@router.get("/profiles")
def list_profiles():
    return {"profiles": list(get_voice_profiles().keys())}
