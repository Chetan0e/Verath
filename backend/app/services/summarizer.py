import logging
from typing import List
from datetime import datetime
from app.services.llm import ask_llm
from app.services.timeline import get_today_timeline, get_recent_timeline
from app.core.logging_config import logger

async def generate_daily_summary(user_id: str) -> str:
    """Generate a summary of today's activities."""
    try:
        timeline = await get_today_timeline(user_id)
        
        if not timeline:
            return "No memories recorded today."
        
        # Extract text for LLM
        text_content = "\n".join([
            f"[{item['time']} - {item['speaker']}]: {item['text']}"
            for item in timeline
        ])
        
        prompt = f"""
Summarize this day's activities and conversations:

{text_content}

Include:
- Key events and topics discussed
- Important tasks or deadlines mentioned
- Notable conversations with different speakers
- Any patterns or insights
- Emotional tone or significant moments

Provide a concise, insightful summary (2-3 paragraphs):
"""
        
        return ask_llm(prompt)
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}", exc_info=True)
        return "Unable to generate summary at this time."

async def generate_period_summary(user_id: str, hours: int = 24) -> str:
    """Generate summary for the last N hours."""
    try:
        timeline = await get_recent_timeline(user_id, hours)
        
        if not timeline:
            return f"No memories recorded in the last {hours} hours."
        
        # Extract text for LLM
        text_content = "\n".join([
            f"[{item['time']} - {item['speaker']}]: {item['text']}"
            for item in timeline
        ])
        
        prompt = f"""
Summarize the activities and conversations from the last {hours} hours:

{text_content}

Focus on:
- Important events and decisions
- Tasks and commitments made
- Key conversations and their outcomes
- Any urgent items or deadlines

Provide a clear, actionable summary (2-3 paragraphs):
"""
        
        return ask_llm(prompt)
    except Exception as e:
        logger.error(f"Error generating period summary: {e}", exc_info=True)
        return "Unable to generate summary at this time."

async def extract_key_insights(user_id: str) -> List[str]:
    """Extract key insights from recent memories."""
    try:
        recent_memories = await get_recent_timeline(user_id, 48)  # Last 2 days
        
        if not recent_memories:
            return []
        
        # Filter for high-importance memories
        important_memories = [
            mem for mem in recent_memories 
            if mem.get('importance', 0) >= 0.6
        ]
        
        if not important_memories:
            return []
        
        text_content = "\n".join([
            f"[{mem['speaker']}]: {mem['text']}"
            for mem in important_memories
        ])
        
        prompt = f"""
Extract the 3-5 most important insights from these conversations:

{text_content}

Focus on:
- Action items and commitments
- Deadlines and time-sensitive information
- Key learnings or realizations
- Important decisions made

Return as a bulleted list, one insight per line:
"""
        
        response = ask_llm(prompt)
        
        # Split into lines and clean up
        lines = [line.strip().lstrip('-').lstrip('*').strip() for line in response.split('\n') if line.strip()]
        
        insights = []
        now = datetime.utcnow()
        for i, line in enumerate(lines[:5]):
            # Try to find a source memory for timestamp, else use now
            source_mem = important_memories[i] if i < len(important_memories) else (important_memories[0] if important_memories else None)
            ts = source_mem.get('timestamp') if source_mem else now
            
            # Convert ts to unix timestamp if it's a datetime object or iso string
            unix_ts = now.timestamp()
            if isinstance(ts, datetime):
                unix_ts = ts.timestamp()
            elif isinstance(ts, str):
                try:
                    unix_ts = datetime.fromisoformat(ts).timestamp()
                except:
                    pass

            insights.append({
                "id": f"insight_{i}_{int(unix_ts)}",
                "text": line,
                "title": "Neural Insight",
                "intent": "insight",
                "timestamp": unix_ts
            })
            
        return insights
    except Exception as e:
        logger.error(f"Error extracting insights: {e}", exc_info=True)
        return []
