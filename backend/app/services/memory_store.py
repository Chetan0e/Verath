import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.services.gemini_embedding import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)


# ── ChromaDB client (persistent, file-backed, concurrent-safe) ──────────────
_chroma_client = chromadb.PersistentClient(
    path=settings.vector_db_path,
    settings=ChromaSettings(anonymized_telemetry=False)
)


def _get_collection(user_id: str):
    """Return (or create) a per-user ChromaDB collection."""
    collection_name = f"user_{user_id.replace('-', '_')}"
    return _chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


# ── MongoDB client ────────────────────────────────────────────────────────────
_mongo_client = AsyncIOMotorClient(settings.mongo_uri)
_db = _mongo_client[settings.database_name]


def _memories_collection():
    return _db["memories"]


# ── Write ─────────────────────────────────────────────────────────────────────
async def store_memory(
    user_id: str,
    text: str,
    metadata: Dict[str, Any],
    created_at: Optional[datetime] = None
) -> str:
    """
    Store a memory in both MongoDB and ChromaDB.

    If ChromaDB persistence fails after MongoDB insertion,
    the MongoDB document is rolled back to avoid storage divergence.
    """

    mem_id = str(uuid.uuid4())
    timestamp = created_at if created_at else datetime.utcnow()

    sanitized_metadata = {
        "user_id": user_id,
        "intent": metadata.get("intent", "unknown"),
        "speaker": metadata.get("speaker", "unknown"),
        "importance": metadata.get("importance", 0.0),
        "lifecycle": metadata.get("lifecycle", "short_term"),
        "timestamp": timestamp.isoformat(),
    }

    embedding = get_embedding(text)

    doc = {
        "_id": mem_id,
        "user_id": user_id,
        "text": text,
        "metadata": metadata,
        "embedding": embedding,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    collection = _get_collection(user_id)

    # Step 1: insert into MongoDB
    await _memories_collection().insert_one(doc)

    # Step 2: persist vector state
    try:
        collection.upsert(
            ids=[mem_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[sanitized_metadata]
        )

    except Exception as e:
        logger.error(
            f"ChromaDB upsert failed for memory {mem_id}, "
            f"rolling back MongoDB insert: {e}"
        )

        # Rollback Mongo insert to maintain consistency
        await _memories_collection().delete_one({"_id": mem_id})

        raise

    return mem_id

async def store_memories_batch(
    user_id: str,
    items: List[Dict[str, Any]]
) -> List[str]:
    """
    Store multiple memories in batch using batch embedding generation.

    Args:
        user_id: User ID
        items: List of dicts with 'text' and 'metadata' keys

    Returns:
        List of memory IDs (same order as input)
    """
    if not items:
        return []

    # Single item - use regular store
    if len(items) == 1:
        return [await store_memory(user_id, items[0]["text"], items[0]["metadata"])]

    timestamp = datetime.utcnow()
    mem_ids = [str(uuid.uuid4()) for _ in items]
    texts = [item["text"] for item in items]

    # Batch generate embeddings
    embeddings = await get_embeddings_batch(texts)

    # Prepare MongoDB documents
    docs = []
    chroma_metadatas = []
    for i, item in enumerate(items):
        metadata = item["metadata"]
        sanitized_metadata = {
            "user_id": user_id,
            "intent": metadata.get("intent", "unknown"),
            "speaker": metadata.get("speaker", "unknown"),
            "importance": metadata.get("importance", 0.0),
            "lifecycle": metadata.get("lifecycle", "short_term"),
            "timestamp": timestamp.isoformat(),
        }
        docs.append({
            "_id": mem_ids[i],
            "user_id": user_id,
            "text": texts[i],
            "metadata": metadata,
            "embedding": embeddings[i],
            "created_at": timestamp,
            "updated_at": timestamp,
        })
        chroma_metadatas.append(sanitized_metadata)

    collection = _get_collection(user_id)

    # Step 1: batch insert into MongoDB
    await _memories_collection().insert_many(docs)

    # Step 2: batch persist vector state
    try:
        collection.upsert(
            ids=mem_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=chroma_metadatas
        )

    except Exception as e:
        logger.error(
            f"Batch ChromaDB upsert failed for user {user_id}, "
            f"rolling back MongoDB batch insert: {e}"
        )
        await _memories_collection().delete_many({
            "_id": {"$in": mem_ids}
        })
        raise

    logger.info(f"do i Batch stored {len(items)} memories for user {user_id}")
    return mem_ids


# ── Read / Search ─────────────────────────────────────────────────────────────
async def search_memories(
    user_id: str,
    query: str,
    limit: int = 5,
    intent_filter: Optional[str] = None,
    min_importance: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Vector similarity search with optional metadata filters.
    Returns a list of memory dicts sorted by relevance.
    """
    collection = _get_collection(user_id)
    try:
        query_embedding = get_embedding(query)
    except Exception:
        logger.warning(
            "Embedding generation unavailable; returning empty search results."
        )
        return []

    # Build ChromaDB where clause
    # ChromaDB doesn't support MongoDB-style operators like $gte
    # We'll filter by intent only and handle importance in post-processing
    where: Dict[str, Any] = {"user_id": user_id}
    if intent_filter:
        where["intent"] = intent_filter
    # Note: min_importance filtering is handled in post-processing due to ChromaDB limitations

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, collection.count()),
            where=where if len(where) > 1 else {"user_id": user_id},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return []

    memories = []
    if results and results["ids"]:
        for i, mem_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            # Post-process importance filter since ChromaDB doesn't support $gte
            if min_importance > 0.0:
                importance = metadata.get("importance", 0.0)
                if importance < min_importance:
                    continue
            memories.append({
                "id": mem_id,
                "text": results["documents"][0][i],
                "metadata": metadata,
                "score": 1 - results["distances"][0][i],  # cosine → similarity
            })

    return memories


# ── Update lifecycle ──────────────────────────────────────────────────────────
async def update_memory_lifecycle(memory_id: str, user_id: str, new_lifecycle: str):
    """Promote or archive a memory by updating its lifecycle stage."""
    col = _memories_collection()
    await col.update_one(
        {"_id": memory_id},
        {"$set": {"metadata.lifecycle": new_lifecycle, "updated_at": datetime.utcnow()}}
    )

    collection = _get_collection(user_id)
    try:
        existing = collection.get(ids=[memory_id], include=["metadatas", "documents", "embeddings"])
        if existing["ids"]:
            meta = existing["metadatas"][0]
            meta["lifecycle"] = new_lifecycle
            collection.update(ids=[memory_id], metadatas=[meta])
    except Exception as e:
        logger.warning(f"ChromaDB lifecycle update failed for {memory_id}: {e}")


# ── Delete ────────────────────────────────────────────────────────────────────
async def delete_memory(memory_id: str, user_id: str):
    """
    Remove a memory from both stores.

    ChromaDB deletion is attempted first to avoid orphaned
    vector embeddings remaining after MongoDB deletion.
    """

    collection = _get_collection(user_id)

    # Step 1: remove vector state first
    try:
        collection.delete(ids=[memory_id])

    except Exception as e:
        logger.error(
            f"ChromaDB delete failed for {memory_id}: {e}"
        )
        raise

    # Step 2: remove MongoDB document
    await _memories_collection().delete_one({"_id": memory_id})


# ── Stats ─────────────────────────────────────────────────────────────────────
async def get_memory_stats(user_id: str) -> Dict[str, Any]:
    col = _memories_collection()
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$metadata.lifecycle",
            "count": {"$sum": 1},
            "avg_importance": {"$avg": "$metadata.importance"},
        }}
    ]
    stats: Dict[str, Any] = {
        "total": 0,
        "by_lifecycle": {"short_term": 0, "long_term": 0, "archived": 0},
        "avg_importance": 0.0,
        "by_intent": {},
        "by_speaker": {},
        "recent_count": 0
    }

    # Get total count
    stats["total"] = await col.count_documents({"user_id": user_id})

    # Get lifecycle stats
    async for doc in col.aggregate(pipeline):
        lifecycle = doc["_id"] or "short_term"
        stats["by_lifecycle"][lifecycle] = doc["count"]
        # Update avg importance if it's the main stat
        if stats["avg_importance"] == 0.0:
             stats["avg_importance"] = doc.get("avg_importance", 0.0)

    # Get intent and speaker stats
    pipeline_extras = [
        {"$match": {"user_id": user_id}},
        {"$facet": {
            "by_intent": [{"$group": {"_id": "$metadata.intent", "count": {"$sum": 1}}}],
            "by_speaker": [{"$group": {"_id": "$metadata.speaker", "count": {"$sum": 1}}}],
            "recent": [{"$match": {"created_at": {"$gte": datetime.utcnow() - timedelta(days=1)}}}, {"$count": "count"}]
        }}
    ]

    async for doc in col.aggregate(pipeline_extras):
        for item in doc.get("by_intent", []):
            if item["_id"]:
                stats["by_intent"][item["_id"]] = item["count"]
        for item in doc.get("by_speaker", []):
            if item["_id"]:
                stats["by_speaker"][item["_id"]] = item["count"]
        if doc.get("recent"):
            stats["recent_count"] = doc["recent"][0]["count"]

    return stats


# ── Get all memories ───────────────────────────────────────────────────────────
async def all_memories_filtered(query: dict) -> List[Dict[str, Any]]:
    """Get memories matching an arbitrary MongoDB query — used by export endpoint
    to push intent and date filters into the database instead of Python memory."""
    col = _memories_collection()
    cursor = col.find(query).sort("created_at", -1)
    memories = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["timestamp"] = doc.get("created_at", datetime.utcnow()).isoformat()
        memories.append(doc)
    return memories


async def all_memories(user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Get all memories for a user from MongoDB."""
    col = _memories_collection()
    cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    memories = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["timestamp"] = doc.get("created_at", datetime.utcnow()).isoformat()
        memories.append(doc)
    return memories

async def filtered_memories(
    user_id: str,
    intent_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10000,
) -> List[Dict[str, Any]]:
    """
    Get memories for a user with filters pushed down to MongoDB.
    Avoids loading the full collection into Python memory before filtering.
    """
    col = _memories_collection()

    # Build query at DB level — only matching documents are transferred
    query: Dict[str, Any] = {"user_id": user_id}

    if intent_filter:
        query["metadata.intent"] = intent_filter

    if start_date or end_date:
        date_filter: Dict[str, Any] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["created_at"] = date_filter

    cursor = col.find(query).sort("created_at", -1).limit(limit)

    memories = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["timestamp"] = doc.get("created_at", datetime.utcnow()).isoformat()
        memories.append(doc)

    return memories
