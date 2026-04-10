from typing import List
from app.services.llm import ask_llm
from app.services.timeline import get_today_timeline, get_recent_timeline

def generate_daily_summary(user_id: str) -> str:
    """Generate a summary of today's activities."""
    timeline = get_today_timeline(user_id)
    
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

Provide a concise, insightful summary:
"""
    
    try:
        return ask_llm(prompt)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def generate_period_summary(user_id: str, hours: int = 24) -> str:
    """Generate summary for the last N hours."""
    timeline = get_recent_timeline(user_id, hours)
    
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

Provide a clear, actionable summary:
"""
    
    try:
        return ask_llm(prompt)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def extract_key_insights() -> List[str]:
    """Extract key insights from recent memories."""
    recent_memories = get_recent_timeline(48)  # Last 2 days
    
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
    
    try:
        response = ask_llm(prompt)
        # Split into lines and clean up
        insights = [line.strip() for line in response.split('\n') if line.strip()]
        return insights[:5]  # Limit to 5 insights
    except Exception as e:
        return [f"Error extracting insights: {str(e)}"]
