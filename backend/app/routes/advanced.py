from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.summarizer import generate_daily_summary, extract_key_insights
from app.services.timeline import get_today_timeline
from app.services.memory_store import get_memory_stats, all_memories
from app.services.auth import get_current_user_id
from app.services.memory_graph import build_memory_graph
from app.core.logging_config import logger
from app.core.cache import cached, get_cache_stats, invalidate_cache

router = APIRouter()


@router.get("/summary")
@cached(ttl_seconds=900, key_prefix="summary")  # 15 minutes cache
async def summary(user_id: str = Depends(get_current_user_id)):
    """Generate daily summary of memories."""
    try:
        logger.info(f"Generating summary for user {user_id}")
        summary_text = await generate_daily_summary(user_id)
        return {"summary": summary_text}
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        return {"summary": "Unable to generate summary at this time."}


@router.get("/timeline")
async def timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    """Get today's timeline of memories with pagination."""
    try:
        logger.info(f"Getting timeline for user {user_id}, page {page}, size {page_size}")
        timeline_data = await get_today_timeline(user_id)
        
        # Apply pagination
        total = len(timeline_data)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_timeline = timeline_data[start_idx:end_idx]
        
        return {
            "timeline": paginated_timeline,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        return {"timeline": [], "pagination": {"total": 0, "page": page, "page_size": page_size, "total_pages": 0}}


@cached(ttl_seconds=900, key_prefix="insights")  # 15 minutes cache
@router.get("/insights")
async def insights(user_id: str = Depends(get_current_user_id)):
    """Extract key insights from memories."""
    try:
        logger.info(f"Extracting insights for user {user_id}")
        insights_data = await extract_key_insights(user_id)
        return {"insights": insights_data}
    except Exception as e:
        logger.error(f"Error extracting insights: {e}", exc_info=True)
        return {"insights": []}

@router.get("/statistics")
@cached(ttl_seconds=300, key_prefix="stats")  # 5 minutes cache
async def statistics(user_id: str = Depends(get_current_user_id)):
    """Get memory statistics."""
    try:
        logger.info(f"Getting statistics for user {user_id}")
        stats = await get_memory_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        return {"total": 0, "by_intent": {}, "by_speaker": {}, "avg_importance": 0.0, "recent_count": 0}


@router.get("/export")
async def export_memories(
    format: str = Query("json", pattern="^(json|csv)$"),
    intent_filter: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Export memories in JSON or CSV format.
    Supports optional intent_filter and date range filtering.
    """
    try:
        logger.info(f"Exporting memories for user {user_id}, format={format}")
        
        # Get all memories
        memories = await all_memories(user_id, limit=10000)
        
        # Apply filters
        if intent_filter:
            memories = [m for m in memories if m.get("metadata", {}).get("intent") == intent_filter]
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            memories = [m for m in memories if (m.get("created_at") if isinstance(m.get("created_at"), datetime) else datetime.fromisoformat(m.get("created_at", ""))) >= start_dt]
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            memories = [m for m in memories if (m.get("created_at") if isinstance(m.get("created_at"), datetime) else datetime.fromisoformat(m.get("created_at", ""))) <= end_dt]
        
        if format == "csv":
            # Generate CSV
            import csv
            from io import StringIO
            from fastapi.responses import StreamingResponse
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "text", "intent", "importance", "speaker", "timestamp", "summary"])
            
            for m in memories:
                writer.writerow([
                    m.get("_id", ""),
                    m.get("text", ""),
                    m.get("metadata", {}).get("intent", ""),
                    m.get("metadata", {}).get("importance", 0.0),
                    m.get("metadata", {}).get("speaker", "unknown"),
                    m.get("created_at", ""),
                    m.get("metadata", {}).get("summary", "")
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=Verath_export_{user_id}.csv"
                }
            )
        else:
            # Return JSON
            return {
                "memories": memories,
                "count": len(memories),
                "exported_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error exporting memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export memories")


@router.post("/cache/invalidate")
async def invalidate_user_cache(user_id: str = Depends(get_current_user_id)):
    """
    Invalidate cache for the current user (admin endpoint).
    Clears all cached data for this user.
    """
    invalidate_cache(pattern=user_id)
    return {"message": f"Cache invalidated for user {user_id}"}


@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics (admin endpoint)."""
    return get_cache_stats()


@router.get("/graph")
@cached(ttl_seconds=600, key_prefix="graph")  # 10 minutes cache
async def memory_graph(
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get memory graph for visualization.
    Returns nodes (memories) and edges (connections based on shared entities).
    """
    try:
        graph_data = await build_memory_graph(user_id, limit=limit)
        return graph_data
    except Exception as e:
        logger.error(f"Error building memory graph: {e}", exc_info=True)
        return {"nodes": [], "links": []}
