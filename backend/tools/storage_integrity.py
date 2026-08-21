"""
Verath Storage Integrity Checker.

Verify that MongoDB and ChromaDB are reachable before
performing storage integrity checks.
"""

from __future__ import annotations

import asyncio

import chromadb
from app.config import settings
from chromadb.config import Settings as ChromaSettings
from motor.motor_asyncio import AsyncIOMotorClient


async def check_mongodb() -> AsyncIOMotorClient:
    """Verify MongoDB connectivity."""
    client = AsyncIOMotorClient(settings.mongo_uri)

    # Ping the server
    await client.admin.command("ping")

    return client


def check_chromadb() -> chromadb.PersistentClient:
    """Verify ChromaDB accessibility."""
    client = chromadb.PersistentClient(
        path=settings.vector_db_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    # Force a read operation
    client.list_collections()

    return client


async def main() -> int:
    print("=" * 40)
    print("Verath Storage Integrity Checker")
    print("=" * 40)

    mongo: AsyncIOMotorClient | None = None

    try:
        print("\nChecking MongoDB connection...")
        mongo = await check_mongodb()
        print("✓ Connected")

        print("\nChecking ChromaDB connection...")
        check_chromadb()
        print("✓ Connected")

        print("\nReady to perform integrity checks.")
        return 0

    except Exception as exc:
        if mongo is None:
            print("✗ MongoDB connection failed")
            print("      Verify MONGO_URI configuration.")
            print()
            print("Possible causes:")
            print("  • MongoDB is not installed")
            print("  • MongoDB service is not running")
            print("  • Docker container is not started")
            print("  • MONGO_URI is incorrect")
            print()
            print("Suggested fixes:")
            print("  • Install MongoDB locally")
            print("  • Or run: docker compose up mongodb")
            print("  • Verify MONGO_URI in .env")
            print()
            print(f"Error: {exc}")
        else:
            print(f"✗ ChromaDB connection failed: {exc}")

        return 1

    finally:
        if mongo is not None:
            mongo.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
