"""
Migration: lifecycle schema consolidation

Runs once against existing documents to:
  1. Set top-level lifecycle_stage = "short_term" on all memories that lack it.
  2. Remove the legacy metadata.lifecycle field (previously held importance
     category strings like "high", "medium", etc.) to eliminate confusion.
  3. Rename metadata.lifecycle → metadata.importance_category where present.

Safe to re-run: all ops are idempotent.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def run():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.database_name]
    col = db["memories"]

    # 1. Backfill lifecycle_stage on docs that lack it
    result = await col.update_many(
        {"lifecycle_stage": {"$exists": False}},
        {"$set": {"lifecycle_stage": "short_term"}}
    )
    print(f"Backfilled lifecycle_stage on {result.modified_count} documents")

    # 2. Rename metadata.lifecycle → metadata.importance_category
    result = await col.update_many(
        {"metadata.lifecycle": {"$exists": True}},
        {
            "$rename": {"metadata.lifecycle": "metadata.importance_category"},
        }
    )
    print(f"Renamed metadata.lifecycle on {result.modified_count} documents")

    client.close()


if __name__ == "__main__":
    asyncio.run(run())