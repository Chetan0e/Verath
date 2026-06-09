import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.services.memory_store import all_memories
from app.core.logging_config import logger
from app.config import settings

async def get_today_timeline(user_id: str) -> List[Dict]:
    """Get timeline of memories from today (last 24 hours)."""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        all_mems = await all_memories(user_id, limit=1000)
        
        # Filter to only recent memories (last 24 hours)
        recent_memories = []
        for mem in all_mems:
            created_at = mem.get('created_at')
            if created_at and created_at >= cutoff_time:
                recent_memories.append(mem)
        
        # Sort by created_at (timestamp) descending
        recent_memories.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
        
        return [
            {
                "time": _format_timestamp(mem.get('created_at')),
                "timestamp": _get_timestamp_seconds(mem.get('created_at')),
                "text": mem.get('metadata', {}).get('cleaned_text') or mem.get('text', ''),
                "speaker": mem.get('metadata', {}).get('speaker') or 'You',
                "importance": mem.get('metadata', {}).get('importance', 0.5),
                "tags": mem.get('metadata', {}).get('tags', []),
                "intent": mem.get('metadata', {}).get('intent'),
                "id": str(mem.get('_id', idx)),
                "audio_file": _get_audio_url(mem.get('metadata', {}).get('audio_file'))
            }
            for idx, mem in enumerate(recent_memories)
        ]
    except Exception as e:
        logger.error(f"Error getting today's timeline: {e}", exc_info=True)
        return []

async def get_date_timeline(user_id: str, date_str: str) -> List[Dict]:
    """Get timeline for specific date (YYYY-MM-DD format)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        all_mems = await all_memories(user_id, limit=1000)
        date_memories = []
        
        for mem in all_mems:
            timestamp = mem.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except:
                        continue
                
                if start_time <= timestamp < end_time:
                    date_memories.append(mem)
        
        # Sort by timestamp
        date_memories.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return [
            {
                "time": _format_timestamp(mem.get('timestamp')),
                "timestamp": _get_timestamp_seconds(mem.get('timestamp')),
                "text": mem.get('metadata', {}).get('cleaned_text') or mem.get('text', ''),
                "speaker": mem.get('metadata', {}).get('speaker') or 'You',
                "importance": mem.get('metadata', {}).get('importance', 0.5),
                "tags": mem.get('metadata', {}).get('tags', []),
                "intent": mem.get('metadata', {}).get('intent'),
                "id": str(mem.get('_id', idx)),
                "audio_file": _get_audio_url(mem.get('metadata', {}).get('audio_file'))
            }
            for idx, mem in enumerate(date_memories)
        ]
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return []
    except Exception as e:
        logger.error(f"Error getting date timeline: {e}", exc_info=True)
        return []

async def get_recent_timeline(user_id: str, hours: int = 24) -> List[Dict]:
    """Get timeline from last N hours."""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        all_mems = await all_memories(user_id, limit=1000)
        recent_memories = []
        
        for mem in all_mems:
            timestamp = mem.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except:
                        continue
                
                if timestamp >= cutoff_time:
                    recent_memories.append(mem)
        
        # Sort by timestamp
        recent_memories.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return [
            {
                "time": _format_timestamp(mem.get('timestamp')),
                "timestamp": _get_timestamp_seconds(mem.get('timestamp')),
                "text": mem.get('metadata', {}).get('cleaned_text') or mem.get('text', ''),
                "speaker": mem.get('metadata', {}).get('speaker') or 'You',
                "importance": mem.get('metadata', {}).get('importance', 0.5),
                "tags": mem.get('metadata', {}).get('tags', []),
                "intent": mem.get('metadata', {}).get('intent'),
                "id": str(mem.get('_id', idx)),
                "audio_file": _get_audio_url(mem.get('metadata', {}).get('audio_file'))
            }
            for idx, mem in enumerate(recent_memories)
        ]
    except Exception as e:
        logger.error(f"Error getting recent timeline: {e}", exc_info=True)
        return []

def _get_timestamp_seconds(timestamp) -> float:
    """Convert timestamp to seconds since epoch (handles both datetime and ISO string)."""
    if not timestamp:
        return 0
    
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    
    if isinstance(timestamp, datetime):
        return timestamp.timestamp()
    
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.timestamp()
        except:
            return 0
    
    return 0

def _format_timestamp(timestamp) -> str:
    """Format timestamp to readable time string."""
    if not timestamp:
        return "Unknown"
    
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except:
            return "Unknown"
    
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%H:%M")
    

def _get_audio_url(audio_file: str) -> str:
    """Convert relative audio file path to full URL."""
    if not audio_file:
        return None
    
    # If already a full URL, return as is
    if audio_file.startswith('http://') or audio_file.startswith('https://'):
        return audio_file
    
    # Replace backslashes with forward slashes for URL
    audio_file = audio_file.replace('\\', '/')
    
    # Construct full URL using the server's base URL
    # Use the configured host and port
    base_url = f"http://{settings.host}:{settings.port}"
    return f"{base_url}/{audio_file}"

async def get_timeline(*args, **kwargs):
    """
    Backward-compatible timeline wrapper.
    """
    return await get_date_timeline(*args, **kwargs)

