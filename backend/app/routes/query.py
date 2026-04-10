from fastapi import APIRouter, Depends
from app.services.query_engine import query_system
from app.services.auth import get_current_user_id

router = APIRouter()

@router.get("/query")
def query(q: str, user_id: str = Depends(get_current_user_id)):
    result = query_system(q, user_id=user_id)
    return {"answer": result["answer"], "context": result["context"]}
