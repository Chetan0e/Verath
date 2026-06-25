import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.query_engine import run_query
from app.models.schema import QueryResponse, QueryRequest
from app.services.auth import get_current_user_id
from app.core.logging_config import logger

router = APIRouter()

@router.get("/query", response_model=QueryResponse)
async def query(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(5, ge=1, le=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    intent_filter: str = Query(None),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    user_id: str = Depends(get_current_user_id)
):
    """Query the memory system with cross-encoder re-ranking and pagination."""
    try:
        logger.info(f"Query from user {user_id}: {q[:50]}...")
        result = await run_query(
            user_id=user_id,
            query=q,
            limit=limit,
            intent_filter=intent_filter,
            min_importance=min_importance
        )
        
        logger.info(f"Query result sources count: {len(result.get('sources', []))}")
        
        # Add pagination metadata
        total_sources = len(result.get("sources", []))
        total_pages = (total_sources + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_sources = result.get("sources", [])[start_idx:end_idx]
        
        return {
    **result,
    "confidence": result.get("confidence_score", 0.0),
    "sources": paginated_sources,
    "pagination": {
        "total": total_sources,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal query error")

_HISTORY_TURNS = 6


@router.post("/query", response_model=QueryResponse)
async def query_with_history(
    body: QueryRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Query the memory system with optional session conversation history."""
    try:
        logger.info(f"Query from user {user_id}: {body.q[:50]}...")
        result = await run_query(
            user_id=user_id,
            query=body.q,
            limit=body.limit,
            intent_filter=body.intent_filter,
            min_importance=body.min_importance,
            history=[{"role": t.role, "content": t.content} for t in body.history[-_HISTORY_TURNS:]],
        )

        logger.info(f"Query result sources count: {len(result.get('sources', []))}")

        return {
            **result,
            "confidence": result.get("confidence_score", 0.0),
            "sources": result.get("sources", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal query error")