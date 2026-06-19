"""
Adapter layer for benchmark integration.

Current implementation uses the deterministic retriever.
Future contributors can replace this with Verath's
actual retrieval/query pipeline without modifying
benchmark logic.
"""

from app.evaluation.rag_benchmark import deterministic_keyword_retriever


def retrieve(query, memories, top_k=5):
    return deterministic_keyword_retriever(
        query=query,
        memories=memories,
        top_k=top_k,
    )
