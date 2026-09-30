"""
BRICS Commons Registry - Configuration Settings.
Independent service configuration with strict privacy controls.
"""

from typing import List, Literal, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RegistrySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Service
    PROJECT_NAME: str = "BRICS Commons Node Registry"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/registry/v1"
    ENVIRONMENT: Literal["dev", "development", "test", "testing", "prod", "production"] = "dev"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = True
    AUTO_APPROVE_DEV: bool = True  # Automatically approves node registrations in development only

    # Security & Keys
    SECRET_KEY: str = "brics-registry-super-secret-key-2026-sovereignty"
    REGISTRY_ADMIN_API_KEY: str = "brics-registry-admin-dev-key-2026"
    SIGNATURE_MAX_AGE_SECONDS: int = 300  # 5 minutes replay protection window
    NONCE_CACHE_TTL_SECONDS: int = 600    # 10 minutes cache for nonces

    # Key Rotation
    KEY_ROTATION_GRACE_HOURS: int = 24

    # Node Heartbeat & Staleness
    HEARTBEAT_INTERVAL_MINUTES: int = 5
    NODE_STALE_THRESHOLD_MINUTES: int = 15  # 3 missed beats

    # CORS & Networking
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Database (PostgreSQL 16 in prod, SQLite async for dev/test)
    DATABASE_URL: str = "sqlite+aiosqlite:///./registry_dev.db"
    SYNC_DATABASE_URL: str = "sqlite:///./registry_dev.db"

    # Privacy Guards (Denylist & Coordinate Precision)
    MAX_COORDINATE_DECIMALS: int = 2  # Disallows high-precision coordinates; max 2 decimals allowed (~1.1km coarse)
    DENIED_PII_FIELDS: List[str] = [
        "farmer_id",
        "farmer_name",
        "full_name",
        "phone_number",
        "national_id",
        "aadhar",
        "cpf",
        "tax_id",
        "email",
        "address",
        "boundary",
        "polygon",
        "cadastre",
        "field_polygon",
        "farm_boundary",
        "raw_image",
        "image_bytes",
        "leaf_photo",
        "leaf_image",
        "photo_bytes"
    ]

    @model_validator(mode="after")
    def validate_production_guards(self) -> "RegistrySettings":
        if self.ENVIRONMENT in ["prod", "production"]:
            if self.AUTO_APPROVE_DEV:
                raise ValueError("CRITICAL SECURITY ERROR: AUTO_APPROVE_DEV cannot be enabled in production.")
            if "sqlite" in self.DATABASE_URL:
                raise ValueError("CRITICAL CONFIGURATION ERROR: SQLite cannot be used in production.")
        return self


settings = RegistrySettings()
