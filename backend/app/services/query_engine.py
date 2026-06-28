import logging
from typing import Any, Dict, List, Optional

from app.services.memory_store import search_memories
from app.services.reranker import async_rerank
from app.services.groq_service import generate_response
from app.config import settings

logger = logging.getLogger(__name__)

# How many candidates to pull from ChromaDB before re-ranking
_N_RETRIEVE = 20
# How many to keep after re-ranking and pass to the LLM
_N_FINAL = 5


async def run_query(
    user_id: str,
    query: str,
    limit: int = 5,
    intent_filter: Optional[str] = None,
    min_importance: float = 0.0,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Full RAG pipeline:
      1. Retrieve N candidates from ChromaDB by vector similarity
      2. Re-rank with cross-encoder
      3. Build a grounded prompt and call Groq
      4. Return answer, sources, and confidence_score
    """

    # ── Step 1: Broad retrieval ───────────────────────────────────────────────
    candidates = await search_memories(
        user_id=user_id,
        query=query,
        limit=_N_RETRIEVE,          # intentionally wider than the final limit
        intent_filter=intent_filter,
        min_importance=min_importance,
    )

    if not candidates:
        return {
            "answer": "I couldn't find any relevant memories for that query.",
            "context": [],
            "sources": [],
            "confidence_score": 0.0,
        }

    # ── Step 2: Cross-encoder re-ranking ─────────────────────────────────────
    reranked = await async_rerank(query=query, candidates=candidates, top_k=min(limit, _N_FINAL))

    # ── Step 3: Build grounded context for LLM ───────────────────────────────
    context_texts = [r["text"] for r in reranked]
    context_block = "\n\n".join(
        f"[Memory {i+1}]: {text}" for i, text in enumerate(context_texts)
    )

    history_block = ""
    if history:
        turns = "\n".join(
            f"{'User' if t['role'] == 'user' else 'Verath'}: {t['content']}"
            for t in history
        )
        history_block = f"Recent conversation:\n{turns}\n\n"

    prompt = (
        f"You are a personal memory assistant. Answer the question using ONLY "
        f"the memories provided below. If the memories don't contain enough "
        f"information, say so honestly.\n\n"
        f"Memories:\n{context_block}\n\n"
        f"{history_block}"
        f"Question: {query}\n\n"
        f"Answer:"
    )

    # ── Step 4: LLM call ──────────────────────────────────────────────────────
    try:
        answer = await generate_response(prompt)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        answer = "I found relevant memories but couldn't generate a response right now."

    # ── Step 5: Build source attribution with confidence ─────────────────────
    sources = []
    for r in reranked:
        meta = r.get("metadata", {})
        sources.append({
            "speaker":    meta.get("speaker", "unknown"),
            "intent":     meta.get("intent", "general"),
            "timestamp":  meta.get("timestamp", ""),
            "importance": meta.get("importance", 0.0),
            "confidence": r.get("confidence", 0.0),   # per-source confidence
        })

    # Overall confidence = top result's confidence score
    confidence_score = reranked[0].get("confidence", 0.0) if reranked else 0.0

    return {
        "answer": answer,
        "context": context_texts,
        "sources": sources,
        "confidence_score": confidence_score,
    }
