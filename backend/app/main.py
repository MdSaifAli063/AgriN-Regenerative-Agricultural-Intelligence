from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, async_engine

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("krishinet.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables and pre-flight checks."""
    logger.info("Initializing KrishiNet-BRICS Engine (AgriN Commons)...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Demo Mode: {settings.DEMO_MODE}")
    
    # In SQLite dev / demo mode, auto-create tables if they don't exist
    if settings.DATABASE_URL.startswith("sqlite"):
        logger.info("Dev/Demo mode with SQLite detected: ensuring tables are initialized...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    yield
    logger.info("Shutting down KrishiNet-BRICS Engine...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## KrishiNet-BRICS (AgriN Commons) Core API
    *One field. Many nations. Shared intelligence.*
    
    An interoperable digital public good delivering:
    - Real-time satellite field intelligence (Sentinel-2 NDVI/NDWI/EVI)
    - Soil health analysis (ISRIC SoilGrids & Soil Health Score)
    - Multi-hazard climate risk forecasting (Open-Meteo & NASA POWER)
    - AI Regenerative Advisory Engine powered by Gemini & FAO/ICAR RAG
    - Crop disease diagnostics with Edge MobileNetV3 & Gemini Multimodal Vision
    - BRICS Federated Interoperability Layer & Flower Learning Node
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 master router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System Telemetry"])
@app.get("/api/health", tags=["System Telemetry"])
async def health_check():
    """Health check endpoint for Kubernetes, Docker, and uptime monitoring."""
    return {
        "status": "healthy",
        "service": "KrishiNet-BRICS Core",
        "version": settings.VERSION,
        "demo_mode": settings.DEMO_MODE,
        "national_node": settings.NATIONAL_NODE_COUNTRY,
        "sovereign_node_id": settings.SOVEREIGN_NODE_ID
    }


@app.get("/", tags=["System Telemetry"])
async def root():
    return {
        "message": "Welcome to KrishiNet-BRICS (AgriN Commons)",
        "tagline": "One field. Many nations. Shared intelligence.",
        "documentation": "/docs",
        "version": settings.VERSION
    }
