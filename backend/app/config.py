from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ── Database ────────────────────────────────────────────────────────────────
    mongo_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string"
    )
    database_name: str = Field(
        default="verath",
        description="Database name"
    )
    app_name: str = Field(
        default="Verath",
        description="Application name"
    )

    # ── Security ───────────────────────────────────────────────────────────────────
    secret_key: str = Field(
        default="default-secret-key-change-in-production-min-32-chars",
        description="Secret key for JWT tokens"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        # Check if secret_key is from Docker secrets file
        secrets_path = Path("/run/secrets/secret_key")
        if secrets_path.exists():
            v = secrets_path.read_text().strip()
        elif len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if v in ("your-super-secret-key", "changeme", "secret"):
            raise ValueError("SECRET_KEY is set to a known insecure default — please change it.")
        return v
    
    login_max_failures: int = Field(
        default=5,
        description="Failed login attempts before an account is locked"
    )
    login_lockout_minutes: int = Field(
        default=15,
        description="Account lockout duration in minutes"
    )

    # ── LLM Providers (Groq + Gemini Fallback) ──────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API Key")
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    llm_provider: str = Field(default="groq", description="Primary LLM provider: groq or gemini")
    groq_model: str = Field(default="llama-3.1-8b-instant", description="Groq model to use")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    llm_timeout: int = Field(default=30, description="LLM request timeout in seconds")
    
    embed_provider: str = Field(default="gemini", description="Embeddings provider")

    # ── Whisper ───────────────────────────────────────────────────────────────
    whisper_model: str = "base"
    whisper_device: str = "cpu"  # default to cpu for stability on Windows
    whisper_compute_type: str = "int8" # space-efficient

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    default_record_seconds: int = 10
    allow_cors: str = "*"
    env: str = "development"

    # ── Storage ───────────────────────────────────────────────────────────────
    vector_db_path: str = "data/chroma_db"
    voice_db_path: str = "data/voices.pkl"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("port")
    @classmethod
    def port_must_be_valid(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError("PORT must be between 1024 and 65535")
        return v

    @field_validator("mongo_uri")
    @classmethod
    def mongo_uri_must_look_valid(cls, v: str) -> str:
        if not (v.startswith("mongodb://") or v.startswith("mongodb+srv://")):
            raise ValueError(
                "MONGO_URI must start with 'mongodb://' or 'mongodb+srv://'"
            )
        return v


# Single import point used everywhere in the app
settings = Settings()
