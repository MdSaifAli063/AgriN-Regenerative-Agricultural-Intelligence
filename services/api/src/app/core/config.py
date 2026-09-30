import os
from typing import List, Literal, Optional
from pydantic import AnyHttpUrl, field_validator, model_validator
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
    ENVIRONMENT: Literal["dev", "development", "test", "testing", "prod", "production"] = "dev"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = True

    # Security & Auth
    SECRET_KEY: str = "krishinet-brics-super-secret-jwt-key-for-hackathon-2026-brics-cooperation"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    DEV_AUTH_BYPASS: bool = True  # Allows fast demo without Keycloak in dev

    # Keycloak OIDC Settings
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "krishinet"
    KEYCLOAK_CLIENT_ID: str = "krishinet-api"
    KEYCLOAK_CLIENT_SECRET: Optional[str] = "krishinet-client-secret-dev"

    @property
    def KEYCLOAK_JWKS_URL(self) -> str:
        return f"{self.KEYCLOAK_SERVER_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    # CORS & Middleware
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]
    RATE_LIMIT_PER_MINUTE: int = 120

    # Sovereign Node Settings
    NODE_ID: str = "node-ind-icar-01"
    NODE_COUNTRY: str = "IND"  # Supports alpha-2 or alpha-3

    # Database (PostgreSQL 16 + PostGIS + pgvector)
    POSTGRES_USER: str = "krishi_admin"
    POSTGRES_PASSWORD: str = "KrishiNetBrics2026!"
    POSTGRES_DB: str = "krishinet_db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "sqlite+aiosqlite:///./krishinet_dev.db"
    SYNC_DATABASE_URL: str = "sqlite:///./krishinet_dev.db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "KrishiMinio2026!"
    MINIO_BUCKET_NAME: str = "krishinet-assets"
    MINIO_BUCKET: str = "krishinet-assets"
    MINIO_SECURE: bool = False

    # External APIs & Models
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_REASONING_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIM: int = 768
    USER_DAILY_TOKEN_LIMIT: int = 50000
    NODE_DAILY_TOKEN_LIMIT: int = 500000
    EARTH_SEARCH_STAC_URL: str = "https://earth-search.aws.element84.com/v1"
    ISRIC_SOILGRIDS_API_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    # Twilio (Optional)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # Meta WhatsApp Cloud API (Optional)
    META_WHATSAPP_TOKEN: Optional[str] = None
    META_WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    META_WEBHOOK_VERIFY_TOKEN: Optional[str] = "krishinet_meta_verify_token_2026"
    META_APP_SECRET: Optional[str] = None

    # Africa's Talking (Optional)
    AFRICASTALKING_USERNAME: Optional[str] = None
    AFRICASTALKING_API_KEY: Optional[str] = None
    AFRICASTALKING_SENDER_ID: Optional[str] = None

    # Messaging Gateway Safety & Defaults
    MESSAGING_DEFAULT_PROVIDER: str = "simulator"  # simulator, twilio, meta, africastalking
    MESSAGING_ENCRYPTION_KEY: str = "7g9sH8_mEsS4g1nG_sEcR3t_kEy_32b_len_0123456789="  # Fernet base64 key
    MESSAGING_PHONE_SALT: str = "krishinet_phone_salt_brics_2026_sovereign"
    MESSAGING_RETENTION_DAYS: int = 30
    MESSAGING_QUIET_HOURS_START: int = 21  # 21:00 (9 PM)
    MESSAGING_QUIET_HOURS_END: int = 6     # 06:00 (6 AM)
    NODE_DAILY_MESSAGING_BUDGET_USD: float = 25.0
    MESSAGING_KILL_SWITCH: bool = False

    @model_validator(mode="after")
    def validate_dev_auth_bypass_in_production(self) -> "Settings":
        """Fail fast if DEV_AUTH_BYPASS is true in production environment."""
        if self.ENVIRONMENT in ["prod", "production"] and self.DEV_AUTH_BYPASS:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: DEV_AUTH_BYPASS cannot be enabled in 'prod' environment."
            )
        return self


settings = Settings()
