from fastapi import APIRouter, HTTPException, Depends
from app.models.schema import AuthRequest
from app.services.database import get_db
from app.services.auth import get_password_hash, verify_password, create_access_token

router = APIRouter()

@router.post("/signup")
async def signup(payload: AuthRequest):
    db = get_db()
    existing_user = await db.users.find_one({"username": payload.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = get_password_hash(payload.password)
    await db.users.insert_one({
        "username": payload.username,
        "password": hashed_password
    })
    return {"msg": "User created successfully"}

@router.post("/login")
async def login(payload: AuthRequest):
    db = get_db()
    user = await db.users.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": str(user["_id"])})
    return {"access_token": token, "token_type": "bearer"}
