import os
import pickle
from typing import Dict, List

import faiss
import numpy as np

from app.config import VECTOR_DB_PATH, VECTOR_META_PATH
from app.models.memory import Memory

DIM = 768

os.makedirs(os.path.dirname(VECTOR_DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(VECTOR_META_PATH), exist_ok=True)

if os.path.exists(VECTOR_DB_PATH):
    index = faiss.read_index(VECTOR_DB_PATH)
else:
    index = faiss.IndexFlatL2(DIM)

if os.path.exists(VECTOR_META_PATH):
    with open(VECTOR_META_PATH, "rb") as file:
        metadata: List[Dict] = pickle.load(file)
else:
    metadata = []


def save():
    faiss.write_index(index, VECTOR_DB_PATH)
    with open(VECTOR_META_PATH, "wb") as file:
        pickle.dump(metadata, file)


def _normalize_memory(data) -> Dict:
    if isinstance(data, Memory):
        return data.model_dump()
    if isinstance(data, dict):
        return Memory(**data).model_dump()
    if isinstance(data, str):
        return Memory(text=data).model_dump()
    raise TypeError("Unsupported memory payload")


def add_memory(data, embedding, user_id: str):
    normalized = _normalize_memory(data)
    normalized["user_id"] = user_id
    vec = np.array([embedding], dtype="float32")
    index.add(vec)
    metadata.append(normalized)
    save()
    return normalized


def search(query_embedding, user_id: str, k: int = 5) -> List[Dict]:
    if not metadata or index.ntotal == 0:
        return []
    
    # Simple filtering after search for now
    # In a production app, we would use a partitioned index or filtered search
    vec = np.array([query_embedding], dtype="float32")
    distances, indices = index.search(vec, min(k * 10, len(metadata))) # Search more to allow filtering
    
    results = []
    for idx in indices[0]:
        if 0 <= idx < len(metadata):
            mem = metadata[idx]
            if mem.get("user_id") == user_id:
                results.append(mem)
                if len(results) >= k:
                    break
    return results


def all_memories(user_id: str) -> List[Dict]:
    return [mem for mem in metadata if mem.get("user_id") == user_id]
