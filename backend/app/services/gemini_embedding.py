import logging
import asyncio
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=settings.gemini_api_key)

def get_embedding(text: str) -> list[float]:
    """Get embedding from Gemini."""
    try:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Error generating embedding with Gemini: {e}")
        # Return an empty vector or raise. Chroma expects a list of floats.
        raise 

async def get_embedding_async(text: str) -> list[float]:
    """Async wrapper for get_embedding"""
    return await asyncio.to_thread(get_embedding, text)

async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch generation of embeddings"""
    try:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
        )
        return [embedding.values for embedding in response.embeddings]
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise 
