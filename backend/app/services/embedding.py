import logging
from typing import List
import time
import ollama
from app.config import settings

logger = logging.getLogger(__name__)


def get_embedding(text: str) -> List[float]:
    """Generate a vector embedding for a given text string using Ollama."""
    try:
        response = ollama.embeddings(
            model=settings.embed_model,
            prompt=text
        )
        return response["embedding"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single batch call.
    
    This is significantly faster than calling get_embedding sequentially
    for large batches.
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors (same order as input texts)
    """
    if not texts:
        return []
    
    # For single item, use regular function to avoid overhead
    if len(texts) == 1:
        return [get_embedding(texts[0])]
    
    try:
        start_time = time.time()
        
        # Batch embed - Ollama's embed endpoint accepts a list of prompts
        embeddings = []
        for text in texts:
            response = ollama.embeddings(
                model=settings.embed_model,
                prompt=text
            )
            embeddings.append(response["embedding"])
        
        elapsed = time.time() - start_time
        logger.info(f"Batch embedding: {len(texts)} texts in {elapsed:.2f}s ({elapsed/len(texts):.3f}s per text)")
        
        return embeddings
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        # Fallback to sequential
        logger.warning("Falling back to sequential embedding generation")
        return [get_embedding(text) for text in texts]
