import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.database import get_db
from app.core.logging_config import logger

class MemoryLifecycleManager:
    """Manages memory lifecycle: short-term -> long-term -> archived."""
    
    IMPORTANCE_THRESHOLD = 0.6  # Threshold for long-term storage
    ARCHIVE_AGE_DAYS = 7  # Days before archiving
    MAX_SHORT_TERM = 100  # Max short-term memories per user
    MAX_LONG_TERM = 1000  # Max long-term memories per user
    
    async def promote_to_long_term(self, user_id: str, memory_id: str) -> bool:
        """Promote a memory from short-term to long-term."""
        try:
            db = get_db()
            if db is None:
                return False
            
            result = await db.memories.update_one(
                {
                    "_id": memory_id,
                    "user_id": user_id,
                    "lifecycle_stage": "short_term"
                },
                {"$set": {"lifecycle_stage": "long_term"}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Promoted memory {memory_id} to long-term")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error promoting memory: {e}", exc_info=True)
            return False
    
    async def archive_memory(self, user_id: str, memory_id: str) -> bool:
        """Archive a memory."""
        try:
            db = get_db()
            if db is None:
                return False
            
            result = await db.memories.update_one(
                {
                    "_id": memory_id,
                    "user_id": user_id
                },
                {"$set": {"lifecycle_stage": "archived"}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Archived memory {memory_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error archiving memory: {e}", exc_info=True)
            return False
    
    async def get_memories_by_stage(
        self, 
        user_id: str, 
        stage: str = "short_term",
        limit: int = 50
    ) -> List[Dict]:
        """Get memories by lifecycle stage."""
        try:
            db = get_db()
            if db is None:
                return []
            
            memories = []
            cursor = db.memories.find({
                "user_id": user_id,
                "lifecycle_stage": stage
            }).sort("timestamp", -1).limit(limit)
            
            async for mem in cursor:
                mem["_id"] = str(mem["_id"])
                memories.append(mem)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error getting memories by stage: {e}", exc_info=True)
            return []
    
    async def enforce_lifecycle_limits(self, user_id: str):
        """Enforce limits on memory stages."""
        try:
            db = get_db()
            if db is None:
                return
            
            # Check short-term limit
            short_term_count = await db.memories.count_documents({
                "user_id": user_id,
                "lifecycle_stage": "short_term"
            })
            
            if short_term_count > self.MAX_SHORT_TERM:
                # Move oldest to long-term or archive
                excess = short_term_count - self.MAX_SHORT_TERM
                cursor = db.memories.find({
                    "user_id": user_id,
                    "lifecycle_stage": "short_term"
                }).sort("timestamp", 1).limit(excess)
                
                async for mem in cursor:
                    if mem.get("importance", 0) >= self.IMPORTANCE_THRESHOLD:
                        await self.promote_to_long_term(user_id, mem["_id"])
                    else:
                        await self.archive_memory(user_id, mem["_id"])
            
            # Check long-term limit
            long_term_count = await db.memories.count_documents({
                "user_id": user_id,
                "lifecycle_stage": "long_term"
            })
            
            if long_term_count > self.MAX_LONG_TERM:
                # Archive oldest
                excess = long_term_count - self.MAX_LONG_TERM
                cursor = db.memories.find({
                    "user_id": user_id,
                    "lifecycle_stage": "long_term"
                }).sort("timestamp", 1).limit(excess)
                
                async for mem in cursor:
                    await self.archive_memory(user_id, mem["_id"])
            
            logger.info(f"Enforced lifecycle limits for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error enforcing lifecycle limits: {e}", exc_info=True)
    
    async def auto_promote_important_memories(self, user_id: str):
        """Automatically promote important memories to long-term."""
        try:
            db = get_db()
            if db is None:
                return

            cursor = db.memories.find({
                "user_id": user_id,
                "lifecycle_stage": "short_term",
                "metadata.importance": {"$gte": self.IMPORTANCE_THRESHOLD},
            })

            promoted_count = 0
            async for mem in cursor:
                promoted = await self.promote_to_long_term(user_id, mem["_id"])
                if promoted:
                    promoted_count += 1

            if promoted_count > 0:
                logger.info(f"Auto-promoted {promoted_count} memories for user {user_id}")

        except Exception as e:
            logger.error(f"Error auto-promoting memories: {e}", exc_info=True)
    
    async def get_lifecycle_stats(self, user_id: str) -> Dict[str, int]:
        """Get statistics about memory lifecycle stages."""
        try:
            db = get_db()
            if db is None:
                return {"short_term": 0, "long_term": 0, "archived": 0}
            
            stats = {}
            for stage in ["short_term", "long_term", "archived"]:
                count = await db.memories.count_documents({
                    "user_id": user_id,
                    "lifecycle_stage": stage
                })
                stats[stage] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting lifecycle stats: {e}", exc_info=True)
            return {"short_term": 0, "long_term": 0, "archived": 0}

memory_lifecycle_manager = MemoryLifecycleManager()

# ── Backward compatibility helper export ────────────────────────────────────

def determine_lifecycle(importance: float) -> str:
    """
    Backward-compatible lifecycle determination helper.

    Preserves older lifecycle classification API expected by tests
    and integrations.
    """
    if importance >= MemoryLifecycleManager.IMPORTANCE_THRESHOLD:
        return "long_term"

    return "short_term"