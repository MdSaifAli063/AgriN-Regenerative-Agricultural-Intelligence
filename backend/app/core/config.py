import os
from typing import List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core App
    PROJECT_NAME: str = "KrishiNet-BRICS (AgriN Commons)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = True

    # Security & JWT
    SECRET_KEY: str = "krishinet-brics-super-secret-jwt-key-for-hackathon-2026-brics-cooperation"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./krishinet_dev.db"
    SYNC_DATABASE_URL: str = "sqlite:///./krishinet_dev.db"
    POSTGRES_USER: str = "krishi_admin"
    POSTGRES_PASSWORD: str = "KrishiNetBrics2026!"
    POSTGRES_DB: str = "krishinet_db"
    POSTGRES_PORT: int = 5432

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "KrishiMinio2026!"
    MINIO_BUCKET_NAME: str = "krishinet-assets"
    MINIO_SECURE: bool = False

    # AI (Gemini)
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL_TEXT: str = "gemini-1.5-flash"
    GEMINI_MODEL_VISION: str = "gemini-1.5-flash"
    GEMINI_MODEL_EMBEDDING: str = "text-embedding-004"

    # External APIs
    EARTH_SEARCH_STAC_URL: str = "https://earth-search.aws.element84.com/v1"
    ISRIC_SOILGRIDS_API_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # Federated Node Configuration
    FLOWER_SERVER_ADDRESS: str = "localhost:8080"
    NATIONAL_NODE_COUNTRY: str = "IND"
    SOVEREIGN_NODE_ID: str = "node-ind-icar-01"


settings = Settings()
