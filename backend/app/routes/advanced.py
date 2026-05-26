from datetime import datetime
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.summarizer import generate_daily_summary, extract_key_insights
from app.services.timeline import get_today_timeline
from app.services.memory_store import get_memory_stats, filtered_memories
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


@router.get("/insights")
@cached(ttl_seconds=900, key_prefix="insights")
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
    Filters are pushed down to MongoDB — no full collection load into Python memory.
    JSON export uses StreamingResponse for memory efficiency on large datasets.
    """
    try:
        logger.info(f"Exporting memories for user {user_id}, format={format}")

        # Parse date filters once
        start_dt: datetime | None = None
        end_dt: datetime | None = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format: YYYY-MM-DD")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format: YYYY-MM-DD")

        # Filters pushed to MongoDB — only matching docs fetched
        memories = await filtered_memories(
            user_id=user_id,
            intent_filter=intent_filter or None,
            start_date=start_dt,
            end_date=end_dt,
            limit=10000,
        )

        if format == "csv":
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
            # Stream JSON — avoids holding full response body in memory
            exported_at = datetime.utcnow().isoformat()

            def json_stream():
                yield f'{{"exported_at":"{exported_at}","count":{len(memories)},"memories":['
                for i, m in enumerate(memories):
                    m_copy = dict(m)
                    if isinstance(m_copy.get("created_at"), datetime):
                        m_copy["created_at"] = m_copy["created_at"].isoformat()
                    if isinstance(m_copy.get("updated_at"), datetime):
                        m_copy["updated_at"] = m_copy["updated_at"].isoformat()
                    yield json.dumps(m_copy, default=str)
                    if i < len(memories) - 1:
                        yield ","
                yield "]}"

            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                json_stream(),
                media_type="application/json",
            )

    except HTTPException:
        raise
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
