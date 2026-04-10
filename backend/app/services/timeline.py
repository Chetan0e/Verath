import time
from datetime import datetime, timedelta
from typing import List, Dict
from app.services.memory_store import all_memories

def get_today_timeline(user_id: str) -> List[Dict]:
    """Get timeline of memories from today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = today.timestamp()
    
    all_mems = all_memories(user_id)
    today_memories = [
        mem for mem in all_mems 
        if mem.get('timestamp', 0) >= today_timestamp
    ]
    
    # Sort by timestamp
    today_memories.sort(key=lambda x: x.get('timestamp', 0))
    
    return [
        {
            "time": datetime.fromtimestamp(mem.get('timestamp', 0)).strftime("%H:%M"),
            "text": mem.get('text', ''),
            "speaker": mem.get('speaker', 'unknown'),
            "importance": mem.get('importance', 0.5),
            "tags": mem.get('tags', []),
            "id": idx
        }
        for idx, mem in enumerate(today_memories)
    ]

def get_date_timeline(user_id: str, date_str: str) -> List[Dict]:
    """Get timeline for specific date (YYYY-MM-DD format)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        all_mems = all_memories(user_id)
        date_memories = [
            mem for mem in all_mems 
            if start_time.timestamp() <= mem.get('timestamp', 0) < end_time.timestamp()
        ]
        
        # Sort by timestamp
        date_memories.sort(key=lambda x: x.get('timestamp', 0))
        
        return [
            {
                "time": datetime.fromtimestamp(mem.get('timestamp', 0)).strftime("%H:%M"),
                "text": mem.get('text', ''),
                "speaker": mem.get('speaker', 'unknown'),
                "importance": mem.get('importance', 0.5),
                "tags": mem.get('tags', []),
                "id": idx
            }
            for idx, mem in enumerate(date_memories)
        ]
    except ValueError:
        return []

def get_recent_timeline(user_id: str, hours: int = 24) -> List[Dict]:
    """Get timeline from last N hours."""
    cutoff_time = time.time() - (hours * 3600)
    
    all_mems = all_memories()
    recent_memories = [
        mem for mem in all_mems 
        if mem.get('timestamp', 0) >= cutoff_time
    ]
    
    # Sort by timestamp
    recent_memories.sort(key=lambda x: x.get('timestamp', 0))
    
    return [
        {
            "time": datetime.fromtimestamp(mem.get('timestamp', 0)).strftime("%H:%M"),
            "text": mem.get('text', ''),
            "speaker": mem.get('speaker', 'unknown'),
            "importance": mem.get('importance', 0.5),
            "tags": mem.get('tags', []),
            "id": idx
        }
        for idx, mem in enumerate(recent_memories)
    ]
