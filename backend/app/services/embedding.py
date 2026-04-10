import requests
from typing import List

from app.config import EMBED_MODEL, OLLAMA_URL


def get_embedding(text: str) -> List[float]:
    """Get embedding for text using Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        if "embedding" not in payload:
            raise ValueError("embedding not returned by Ollama")
        return payload["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}")
        # Return zero embedding as fallback
        return [0.0] * 768

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for multiple texts."""
    embeddings = []
    for text in texts:
        embedding = get_embedding(text)
        embeddings.append(embedding)
    return embeddings
