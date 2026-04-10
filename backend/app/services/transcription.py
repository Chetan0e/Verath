from functools import lru_cache

from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL


@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    return WhisperModel(WHISPER_MODEL)


def transcribe(audio_path: str) -> str:
    model = get_model()
    segments, _ = model.transcribe(audio_path)
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())
