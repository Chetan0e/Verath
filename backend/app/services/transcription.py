import logging
from functools import lru_cache
from faster_whisper import WhisperModel
from app.config import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    try:
        logger.info(f"Loading Whisper model '{settings.whisper_model}' on {settings.whisper_device} ({settings.whisper_compute_type})")
        return WhisperModel(
            settings.whisper_model, 
            device=settings.whisper_device, 
            compute_type=settings.whisper_compute_type
        )
    except Exception as e:
        logger.error(f"Failed to load Whisper model on {settings.whisper_device}: {e}")
        if settings.whisper_device != "cpu":
            logger.info("Retrying on CPU...")
            return WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        raise


def transcribe(audio_path: str) -> str:
    try:
        model = get_model()
        segments, info = model.transcribe(audio_path, beam_size=5, language='en')
        segments = list(segments)
        logger.info(f"Whisper found {len(segments)} segments. Language: {info.language} ({info.language_probability:.2f})")
        for i, s in enumerate(segments):
            logger.debug(f"Segment {i}: '{s.text}' (conf: {s.avg_logprob:.2f})")
        
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        logger.info(f"Final transcribed text: '{text}'")
        return text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        # Clear the lru_cache so the next call attempts to reload the model
        # rather than reusing a potentially corrupted or stale instance.
        # Without this, a model that enters an error state (e.g. GPU OOM)
        # is used indefinitely for the lifetime of the process.
        get_model.cache_clear()
        logger.info("Whisper model cache cleared — will reload on next transcription attempt.")
        raise
