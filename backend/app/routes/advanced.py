from collections import defaultdict
from datetime import datetime
from io import BytesIO, StringIO
import csv

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.services.summarizer import generate_daily_summary, extract_key_insights
from app.services.timeline import get_today_timeline
from app.services.memory_store import get_memory_stats, all_memories, all_memories_filtered
from app.services.auth import get_current_user_id
from app.services.digest import generate_and_store_digest, get_latest_digest
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
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
    intent_filter: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Export memories in JSON, CSV, or PDF format.
    Supports optional intent_filter and date range filtering.
    """
    try:
        logger.info(f"Exporting memories for user {user_id}, format={format}")

        # Build MongoDB query filters to avoid loading all documents into memory
        mongo_query: dict = {"user_id": user_id}
        if intent_filter:
            mongo_query["metadata.intent"] = intent_filter
        date_filter: dict = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date)
        if date_filter:
            mongo_query["created_at"] = date_filter

        # Fetch only matching documents from MongoDB — no Python-side filtering needed
        memories = await all_memories_filtered(mongo_query)
        
        if format == "csv":
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

        # ── PDF ───────────────────────────────────────────────────────────────
        elif format == "pdf":
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                HRFlowable,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            styles = getSampleStyleSheet()
            BRAND_DARK = colors.HexColor("#2d2d6b")
            BRAND_LIGHT = colors.HexColor("#f0f0fa")

            title_style = ParagraphStyle(
                "VTitle",
                parent=styles["Heading1"],
                fontSize=22,
                spaceAfter=4,
                textColor=BRAND_DARK,
            )
            subtitle_style = ParagraphStyle(
                "VSubtitle",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.grey,
                spaceAfter=10,
            )
            date_header_style = ParagraphStyle(
                "VDateHeader",
                parent=styles["Heading2"],
                fontSize=12,
                spaceBefore=14,
                spaceAfter=4,
                textColor=BRAND_DARK,
            )
            body_style = ParagraphStyle(
                "VBody",
                parent=styles["Normal"],
                fontSize=9,
                leading=13,
                spaceAfter=3,
            )
            meta_style = ParagraphStyle(
                "VMeta",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                spaceAfter=6,
            )

            elements = []

            # Header block
            elements.append(Paragraph("Verath Memory Export", title_style))
            elements.append(Paragraph(
                f"User: {user_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Total memories: {len(memories)}",
                subtitle_style,
            ))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_DARK))
            elements.append(Spacer(1, 0.4 * cm))

            # Summary table
            elements.append(Paragraph("Export Summary", date_header_style))
            summary_rows = [
                ["Metric", "Value"],
                ["Total memories", str(len(memories))],
                ["Intent filter", intent_filter or "None"],
                ["Date range", f"{start_date or 'Beginning'} → {end_date or 'Now'}"],
            ]
            summary_table = Table(summary_rows, colWidths=[5 * cm, 11 * cm])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.6 * cm))

            # Memory records grouped by date (newest first)
            elements.append(Paragraph("Memory Records", date_header_style))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

            date_groups: dict = defaultdict(list)
            for m in memories:
                raw_ts = m.get("created_at", "")
                try:
                    if isinstance(raw_ts, datetime):
                        date_key = raw_ts.strftime("%Y-%m-%d")
                    else:
                        date_key = datetime.fromisoformat(str(raw_ts)).strftime("%Y-%m-%d")
                except Exception:
                    date_key = "Unknown Date"
                date_groups[date_key].append(m)

            for date_key in sorted(date_groups.keys(), reverse=True):
                elements.append(Paragraph(f"&#128197; {date_key}", date_header_style))

                for m in date_groups[date_key]:
                    meta = m.get("metadata", {})
                    text = m.get("text", "")
                    intent = meta.get("intent", "general")
                    importance = meta.get("importance", 0.0)
                    speaker = meta.get("speaker", "unknown")
                    summary_text = meta.get("summary", "")

                    elements.append(Paragraph(
                        f"<b>[{intent.upper()}]</b> &nbsp; Importance: <b>{round(float(importance) * 100)}%</b>"
                        f" &nbsp;|&nbsp; Speaker: <b>{speaker}</b>",
                        meta_style,
                    ))
                    elements.append(Paragraph(text, body_style))
                    if summary_text:
                        elements.append(Paragraph(f"<i>&#x2192; {summary_text}</i>", meta_style))
                    elements.append(HRFlowable(
                        width="100%", thickness=0.3, color=colors.HexColor("#e0e0e0")
                    ))
                    elements.append(Spacer(1, 0.1 * cm))

            doc.build(elements)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=Verath_export_{user_id}.pdf"
                }
            )

        # ── JSON (default) ────────────────────────────────────────────────────
        else:
            # Stream JSON response to avoid holding entire dataset in memory
            import json
            from fastapi.responses import StreamingResponse

            exported_at = datetime.utcnow().isoformat()
            count = len(memories)

            def json_stream():
                yield f'{{"memories": '
                yield "["
                for i, m in enumerate(memories):
                    yield json.dumps(m, default=str)
                    if i < count - 1:
                        yield ","
                yield ']' + f', "count": {count}, "exported_at": "{exported_at}"}}'

            return StreamingResponse(
                json_stream(),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=Verath_export_{user_id}.json"
                }
            )
            
    except Exception as e:
        logger.error(f"Error exporting memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export memories")

    except Exception as e:
        logger.error(f"Error exporting memories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export memories")

@router.get("/digest/latest")
async def latest_digest(user_id: str = Depends(get_current_user_id)):
    """Return the most recent stored digest for the current user."""
    doc = await get_latest_digest(user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No digest available yet.")
    return {
        "generated_at": doc["generated_at"].isoformat(),
        "window_hours": doc["window_hours"],
        "summary": doc["summary"],
    }

@router.post("/digest/generate")
async def trigger_digest(
    window_hours: int = Query(168, ge=1, le=720),
    user_id: str = Depends(get_current_user_id),
):
    """Manually trigger a digest for the current user."""
    doc = await generate_and_store_digest(user_id, window_hours=window_hours)
    return {
        "generated_at": doc["generated_at"].isoformat(),
        "summary": doc["summary"],
    }