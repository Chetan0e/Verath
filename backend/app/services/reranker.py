import asyncio
import logging
from typing import List, Dict, Any

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_cross_encoder: CrossEncoder = None


def _get_cross_encoder() -> CrossEncoder:
    """Lazy-load the cross-encoder model (downloads once, cached locally)."""
    global _cross_encoder
    if _cross_encoder is None:
        logger.info(f"Loading cross-encoder model: {_MODEL_NAME}")
        _cross_encoder = CrossEncoder(_MODEL_NAME, max_length=512)
        logger.info("Cross-encoder loaded successfully")
    return _cross_encoder


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Re-rank a list of candidate memory dicts against the query using a cross-encoder.

    Each candidate must have a "text" key.
    Returns top_k candidates sorted by cross-encoder score descending,
    with a "rerank_score" and "confidence" field added to each.
    """
    if not candidates:
        return []

    model = _get_cross_encoder()

    # Build (query, candidate_text) pairs for the model
    pairs = [(query, c["text"]) for c in candidates]

    # Score all pairs — returns a numpy array of logits
    raw_scores = model.predict(pairs)

    # Attach scores to candidates
    scored = []
    for i, candidate in enumerate(candidates):
        score = float(raw_scores[i])
        scored.append({
            **candidate,
            "rerank_score": score,
        })

    # Sort by cross-encoder score descending
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    top = scored[:top_k]

    # Normalise scores into a 0-1 confidence value using sigmoid
    # This gives an intuitive confidence the user can read
    import math
    for item in top:
        item["confidence"] = round(1 / (1 + math.exp(-item["rerank_score"])), 3)

    return top

async def async_rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Async wrapper around rerank().

    Offloads the CPU-bound cross-encoder forward pass to the default
    ThreadPoolExecutor so the asyncio event loop stays free to handle
    other requests concurrently.
    """
    return await asyncio.to_thread(rerank, query, candidates, top_k)
