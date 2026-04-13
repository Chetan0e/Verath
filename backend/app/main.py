import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging_config import setup_logging
from app.workers.background_worker import start_worker
from app.services.reminder_service import check_and_fire_reminders
from app.services.database import get_db

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routes.auth import router as auth_router
from app.routes.query import router as query_router
from app.routes.record import router as record_router
from app.routes.advanced import router as advanced_router
from app.routes.speaker import router as speaker_router
from app.routes.privacy import router as privacy_router
from app.routes.pipeline_routes import router as pipeline_router
from app.routes.reminders import router as reminders_router
from app.routes.memories import router as memories_router
from app.routes.websocket import router as websocket_router

setup_logging()
logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


async def warm_chroma_collections():
    """
    On startup, ensure ChromaDB collections exist for all users who have memories.
    Rebuild missing collections from MongoDB documents.
    """
    logger.info("Warming ChromaDB collections...")
    
    try:
        db = get_db()
        
        # Get all unique user_ids from memories
        user_ids = await db["memories"].distinct("user_id")
        
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from app.config import settings
        from app.services.embedding import get_embedding
        
        chroma_client = chromadb.PersistentClient(
            path=settings.vector_db_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        for user_id in user_ids:
            collection_name = f"user_{user_id.replace('-', '_')}"
            
            try:
                # Check if collection exists
                collection = chroma_client.get_collection(name=collection_name)
                logger.debug(f"Collection {collection_name} exists for user {user_id}")
            except Exception:
                # Collection doesn't exist - rebuild from MongoDB
                logger.warning(f"Collection {collection_name} missing for user {user_id}, rebuilding from MongoDB...")
                
                # Get all memories for this user
                memories = []
                async for doc in db["memories"].find({"user_id": user_id}):
                    memories.append(doc)
                
                if memories:
                    # Create collection
                    collection = chroma_client.create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"}
                    )
                    
                    # Rebuild embeddings and upsert
                    ids = [str(doc["_id"]) for doc in memories]
                    texts = [doc["text"] for doc in memories]
                    metadatas = []
                    embeddings = []
                    
                    for doc in memories:
                        metadata = doc.get("metadata", {})
                        sanitized_metadata = {
                            "user_id": user_id,
                            "intent": metadata.get("intent", "unknown"),
                            "speaker": metadata.get("speaker", "unknown"),
                            "importance": metadata.get("importance", 0.0),
                            "lifecycle": metadata.get("lifecycle", "short_term"),
                            "timestamp": doc.get("created_at", datetime.utcnow()).isoformat(),
                        }
                        metadatas.append(sanitized_metadata)
                        
                        # Use stored embedding or regenerate
                        if "embedding" in doc:
                            embeddings.append(doc["embedding"])
                        else:
                            embeddings.append(get_embedding(doc["text"]))
                    
                    collection.upsert(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )
                    
                    logger.info(f"Rebuilt collection {collection_name} with {len(memories)} memories")
        
        logger.info("ChromaDB collection warming complete")
        
    except Exception as e:
        logger.error(f"Error warming ChromaDB collections: {e}", exc_info=True)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SecondBrain starting up...")

    # 1. Connect to MongoDB and create indexes
    from app.services.database import connect_to_mongo, close_mongo_connection
    await connect_to_mongo()

    # 2. Start background worker queue
    start_worker()

    # 3. Start reminder scheduler — runs check_and_fire_reminders every 15 min
    _scheduler.add_job(
        check_and_fire_reminders,
        trigger="interval",
        minutes=15,
        id="reminder_check",
        replace_existing=True,
        misfire_grace_time=60,   # allow 60s late start before skipping
    )
    _scheduler.start()
    logger.info("Reminder scheduler started (interval: 15 min)")

    yield

    # Shutdown
    _scheduler.shutdown(wait=False)
    await close_mongo_connection()
    logger.info("SecondBrain shut down cleanly")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SecondBrain API",
    version="3.0.0",
    description="AI-powered personal memory system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_cors.split(",") if settings.env == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(query_router)
app.include_router(record_router)
app.include_router(advanced_router)
app.include_router(speaker_router)
app.include_router(privacy_router)
app.include_router(pipeline_router)
app.include_router(memories_router)
app.include_router(reminders_router)
app.include_router(websocket_router)


@app.get("/status")
async def status():
    # Comprehensive health check
    from app.services.memory_store import _memories_collection
    from app.services.database import get_db
    import chromadb

    health_status = {
        "status": "running",
        "version": "3.0.0",
        "scheduler": "running" if _scheduler.running else "stopped",
        "services": {}
    }

    # Check MongoDB
    try:
        db = get_db()
        if db:
            await db.command("ping")
            col = _memories_collection()
            total_nodes = await col.count_documents({})
            health_status["services"]["mongodb"] = "healthy"
            health_status["nodes"] = total_nodes
        else:
            health_status["services"]["mongodb"] = "unhealthy"
            health_status["nodes"] = 0
    except Exception as e:
        health_status["services"]["mongodb"] = f"unhealthy: {str(e)}"
        health_status["nodes"] = 0

    # Check ChromaDB
    try:
        from app.config import settings
        client = chromadb.PersistentClient(path=settings.vector_db_path)
        client.heartbeat()
        health_status["services"]["chromadb"] = "healthy"
    except Exception as e:
        health_status["services"]["chromadb"] = f"unhealthy: {str(e)}"

    # Check Ollama
    try:
        import requests
        response = requests.get(f"{settings.ollama_url}/api/tags", timeout=2)
        if response.status_code == 200:
            health_status["services"]["ollama"] = "healthy"
        else:
            health_status["services"]["ollama"] = "unhealthy"
    except Exception as e:
        health_status["services"]["ollama"] = f"unhealthy: {str(e)}"

    # Overall status
    if all(v == "healthy" for v in health_status["services"].values()):
        health_status["overall"] = "healthy"
    else:
        health_status["overall"] = "degraded"

    return health_status


@app.get("/")
async def root():
    return {"message": "SecondBrain API v3.0.0"}
