from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI, DATABASE_NAME

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    db_instance.client = AsyncIOMotorClient(MONGO_URI)
    db_instance.db = db_instance.client[DATABASE_NAME]
    print(f"Connected to MongoDB at {MONGO_URI}")

async def close_mongo_connection():
    db_instance.client.close()
    print("Closed MongoDB connection")

def get_db():
    return db_instance.db
