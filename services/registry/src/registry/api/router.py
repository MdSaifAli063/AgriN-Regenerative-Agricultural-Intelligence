"""
BRICS Commons Registry - Unified API Router Assembly.
"""

from fastapi import APIRouter
from registry.api.v1.nodes import router as nodes_router
from registry.api.v1.discovery import router as discovery_router
from registry.api.v1.health import router as health_router

api_router = APIRouter()

# Attach API v1 endpoints
api_router.include_router(nodes_router, prefix="/registry/v1")
api_router.include_router(discovery_router)
api_router.include_router(health_router)
