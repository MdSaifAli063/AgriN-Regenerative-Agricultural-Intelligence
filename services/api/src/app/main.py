from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from app.api.router import api_router, interop_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middlewares import setup_middlewares
from app.db.base import Base
from app.db.session import async_engine
from app.services.storage import storage_service

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("krishinet.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]..."
    )
    logger.info(f"Sovereign Node ID: {settings.NODE_ID} (Country: {settings.NODE_COUNTRY})")
    logger.info(f"Demo Mode: {settings.DEMO_MODE} | Dev Auth Bypass: {settings.DEV_AUTH_BYPASS}")

    # Auto-initialize tables in dev sqlite mode
    if settings.DATABASE_URL.startswith("sqlite"):
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Local dev database tables initialized.")

    # Auto-ensure MinIO bucket exists
    storage_service.ensure_bucket_exists()

    yield
    logger.info("Gracefully stopping KrishiNet-BRICS API...")


def create_app() -> FastAPI:
    """FastAPI application factory for KrishiNet-BRICS."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="""
        ## KrishiNet-BRICS (AgriN Commons) Sovereign API
        *One field. Many nations. Shared intelligence.*
        
        Sovereign Digital Public Good providing:
        - 60-Second Field Onboarding with GeoJSON & GPS
        - Sentinel-2 Satellite Vegetation Indices & 90-Day Trends
        - ISRIC SoilGrids Physical-Chemical Health Scoring
        - Multi-Hazard Agro-Climate Risk Forecasting
        - AI Regenerative Advisories & Agrochemical Safety Guards
        - Keycloak OIDC Authentication & Granular Consent Control
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middlewares & Handlers
    setup_middlewares(app)
    register_exception_handlers(app)

    # Routes
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.API_V1_STR)
    # OGC STAC 1.0 and JSON-LD contexts – served at /stac and /contexts
    app.include_router(interop_router)

    @app.get("/.well-known/agrin-node.json", tags=["Node Passport"])
    async def get_node_passport():
        return {
            "node_id": settings.NODE_ID,
            "country_code": settings.NODE_COUNTRY,
            "organisation_name": f"KrishiNet Sovereign Node ({settings.NODE_COUNTRY})",
            "version": settings.VERSION,
            "capabilities": [
                "stac-1.0.0",
                "geojson-rfc7946",
                "jsonld-agrovoc",
                "flower-fl-grpc",
                "mobilenetv3-disease-edge",
            ],
            "standards_supported": [
                "OGC-STAC-1.0.0",
                "GeoJSON-RFC7946",
                "JSON-LD-AGROVOC",
                "OpenAPI-3.1",
                "Flower-FL",
            ],
            "licences": ["Apache-2.0", "CC-BY-4.0"],
            "contact": "admin@krishinet.org",
            "data_policy": {
                "raw_data_residency": "100% on-soil",
                "egress_enforcement": "Sovereign Egress Gate with Differential Privacy and k-anonymity",
                "min_k_anonymity": 5,
                "max_coordinate_decimals": 2,
            },
        }

    return app


app = create_app()
