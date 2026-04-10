from app.services.embedding import get_embedding
from app.services.llm import ask_llm_with_context
from app.services.memory_store import search, all_memories
from typing import List, Dict


def query_system(user_query: str, user_id: str, limit: int = 5) -> Dict:
    """Query the memory system with RAG."""
    try:
        # Get embedding for the query
        query_embedding = get_embedding(user_query)
        
        # Search for relevant memories
        memories = search(query_embedding, user_id=user_id, k=limit)
        
        if not memories:
            return {"answer": "I don't have any memories related to your question.", "context": []}
        
        # Build context from memories
        context_items = [item.get("text", "") for item in memories if item.get("text")]
        context = "\n".join([
            f"[{mem.get('speaker', 'unknown')}]: {mem.get('text', '')}"
            for mem in memories
        ])
        
        # Ask LLM with context
        answer = ask_llm_with_context(user_query, context)
        
        return {"answer": answer, "context": context_items}
        
    except Exception as e:
        return {"answer": f"Error querying system: {str(e)}", "context": []}

def query_memories_by_speaker(speaker: str, limit: int = 10) -> List[dict]:
    """Get all memories from a specific speaker."""
    all_mems = all_memories()
    speaker_memories = [
        mem for mem in all_mems 
        if mem.get('speaker', '').lower() == speaker.lower()
    ]
    
    # Sort by timestamp (most recent first)
    speaker_memories.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return speaker_memories[:limit]
