import logging
import asyncio
import hashlib
import math
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini client lazily
_client = None
client = None


def _fallback_embedding(text: str, dim: int = 768) -> list[float]:
    """Generate a deterministic normalized pseudo-embedding when Gemini API key is missing or fails."""
    seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vector = []
    current = seed_hash
    while len(vector) < dim:
        for byte in current:
            vector.append(float(byte) / 255.0 - 0.5)
            if len(vector) >= dim:
                break
        current = hashlib.sha256(current).digest()
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


def get_client():
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            return None
        try:
            _client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")
            _client = None
    return _client

def get_embedding(text: str) -> list[float]:
    """Get embedding from Gemini with fallback."""
    try:
        active_client = client or get_client()
        if active_client is not None:
            response = active_client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
            )
            return response.embeddings[0].values
    except Exception as e:
        logger.warning(f"Gemini embedding API call failed, using fallback embedding: {e}")
    
    return _fallback_embedding(text)

async def get_embedding_async(text: str) -> list[float]:
    """Async wrapper for get_embedding"""
    return await asyncio.to_thread(get_embedding, text)

async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch generation of embeddings with fallback."""
    try:
        active_client = client or get_client()
        if active_client is not None:
            response = active_client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
            )
            return [embedding.values for embedding in response.embeddings]
    except Exception as e:
        logger.warning(f"Gemini batch embedding API call failed, using fallback: {e}")
    
    return [_fallback_embedding(t) for t in texts]

