from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOW_CORS
from app.routes import advanced, auth, privacy, query, record, speaker
from app.services.database import connect_to_mongo, close_mongo_connection

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SecondBrain")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SecondBrain core...")
    await connect_to_mongo()
    yield
    await close_mongo_connection()
    logger.info("SecondBrain core shut down.")

app = FastAPI(title="SecondBrain", version="1.0.0", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal neural error occurred. Please try again later."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_CORS if ALLOW_CORS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(record.router, tags=["record"])
app.include_router(query.router, tags=["query"])
app.include_router(advanced.router, tags=["advanced"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(privacy.router, prefix="/privacy", tags=["privacy"])
app.include_router(speaker.router, prefix="/speaker", tags=["speaker"])


@app.get("/")
def root():
    return {"name": "SecondBrain", "status": "ok"}
