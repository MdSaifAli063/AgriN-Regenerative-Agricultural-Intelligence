"""
BRICS Commons Registry - FastAPI Application Main Entrypoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from registry.api.router import api_router
from registry.core.config import settings
from registry.core.privacy_guard import PrivacyViolationError
from registry.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "BRICS Commons Registry: Metadata, signed node identities, model cards, "
        "and aggregated statistics repository for sovereign digital public goods. "
        "Zero-PII and coarse-spatial data residency strictly enforced."
    ),
    openapi_url="/registry/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PrivacyViolationError)
async def privacy_violation_handler(request: Request, exc: PrivacyViolationError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


# Attach API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "BRICS Commons Registry",
        "version": settings.VERSION,
        "federation_standard": "BRICS-AgriN-2026.1",
        "discovery_url": "/.well-known/agrin-registry.json",
        "docs_url": "/docs",
    }
