from fastapi import APIRouter, Depends
from app.services.auth import get_current_user_id
from app.services.privacy import is_private, toggle_privacy

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/")
async def get_privacy(user_id: str = Depends(get_current_user_id)):
    return {"private": await is_private(user_id)}


@router.post("/toggle")
async def toggle(user_id: str = Depends(get_current_user_id)):
    return {"private": await toggle_privacy(user_id)}