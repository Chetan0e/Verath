from fastapi import APIRouter, Depends
from app.services.summarizer import generate_daily_summary, extract_key_insights
from app.services.timeline import get_today_timeline
from app.services.auth import get_current_user_id

router = APIRouter()

@router.get("/summary")
def summary(user_id: str = Depends(get_current_user_id)):
    return {"summary": generate_daily_summary(user_id)}

@router.get("/timeline")
def timeline(user_id: str = Depends(get_current_user_id)):
    return {"timeline": get_today_timeline(user_id)}

@router.get("/insights")
def insights(user_id: str = Depends(get_current_user_id)):
    return {"insights": extract_key_insights(user_id)}
