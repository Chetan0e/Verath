import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
VECTOR_DB_PATH = str(BASE_DIR / os.getenv("VECTOR_DB_PATH", "data/vector_db/index.faiss"))
VECTOR_META_PATH = str(BASE_DIR / os.getenv("VECTOR_META_PATH", "data/vector_db/meta.pkl"))
VOICE_DB_PATH = str(BASE_DIR / os.getenv("VOICE_DB_PATH", "data/voices.pkl"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEFAULT_RECORD_SECONDS = int(os.getenv("DEFAULT_RECORD_SECONDS", "10"))
ALLOW_CORS = [item.strip() for item in os.getenv("ALLOW_CORS", "*").split(",") if item.strip()]

# Database & Authentication
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "secondbrain")
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week
