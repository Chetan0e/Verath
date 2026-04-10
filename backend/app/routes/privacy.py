from fastapi import APIRouter

from app.services.privacy import is_private, toggle_privacy

router = APIRouter()


@router.get("/")
def get_privacy():
    return {"private": is_private()}


@router.post("/toggle")
def toggle():
    return {"private": toggle_privacy()}
