from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    # Configure connection pooling and timeouts
    db_instance.client = AsyncIOMotorClient(
        settings.mongo_uri,
        maxPoolSize=100,
        minPoolSize=10,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
    )
    db_instance.db = db_instance.client[settings.database_name]
    print(f"Connected to MongoDB at {settings.mongo_uri}")

    # Create indexes on startup
    await create_indexes()

async def close_mongo_connection():
    db_instance.client.close()
    print("Closed MongoDB connection")

def get_db():
    return db_instance.db

async def create_indexes():
    """Create MongoDB indexes for common query patterns."""
    try:
        db = db_instance.db

        # Users collection indexes
        await db["users"].create_index("username", unique=True)

        # Memories collection indexes
        await db["memories"].create_index([("user_id", 1), ("created_at", -1)])
        await db["memories"].create_index([("user_id", 1), ("intent", 1)])
        await db["memories"].create_index([("user_id", 1), ("importance", -1)])
        await db["memories"].create_index([("user_id", 1), ("lifecycle_stage", 1)])
        await db["memories"].create_index([("user_id", 1), ("metadata.speaker", 1)])
        await db["memories"].create_index("created_at", expireAfterSeconds=2592000)  # 30 days TTL for old documents if needed

        # Alerts collection indexes
        await db["alerts"].create_index([("user_id", 1), ("acknowledged", 1)])
        await db["alerts"].create_index([("user_id", 1), ("alerted_at", -1)])
        await db["alerts"].create_index("alerted_at", expireAfterSeconds=604800)  # 7 days TTL

        # Worker tasks indexes
        await db["worker_tasks"].create_index([("status", 1), ("created_at", -1)])
        await db["worker_tasks"].create_index("created_at", expireAfterSeconds=604800)  # 7 days TTL

        # Blacklisted tokens for logout
        await db["blacklisted_tokens"].create_index("jti", unique=True)
        await db["blacklisted_tokens"].create_index("exp", expireAfterSeconds=0)  # TTL based on token expiry

        # Audit logs
        await db["audit_logs"].create_index([("username", 1), ("timestamp", -1)])
        await db["audit_logs"].create_index([("event_type", 1), ("timestamp", -1)])
        await db["audit_logs"].create_index([("ip_address", 1), ("timestamp", -1)])
        await db["audit_logs"].create_index("timestamp", expireAfterSeconds=7776000)  # 90 days TTL

        print("MongoDB indexes created successfully")
    except Exception as e:
        print(f"Warning: Failed to create indexes: {e}")
