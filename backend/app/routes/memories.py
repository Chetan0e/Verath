import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.auth import get_current_user_id
from app.services.memory_store import delete_memory, _memories_collection
from app.core.logging_config import logger

router = APIRouter()


@router.delete("/memory/{memory_id}")
async def delete_memory_endpoint(
    memory_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a memory by ID.
    Verifies memory belongs to authenticated user before deleting.
    Deletes from both MongoDB and ChromaDB.
    """
    try:
        # Verify memory belongs to user
        col = _memories_collection()
        memory = await col.find_one({"_id": memory_id})
        
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        if memory.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this memory"
            )
        
        # Delete from both MongoDB and ChromaDB
        await delete_memory(memory_id, user_id)
        
        logger.info(f"Deleted memory {memory_id} for user {user_id}")
        return {"message": "Memory deleted successfully", "id": memory_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory"
        )
