"""
BRICS Commons Registry - Health & Readiness Endpoint.
"""

from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from registry.core.config import settings
from registry.db.session import get_db

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health", summary="Health check endpoint")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict:
    db_ok = False
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "brics-commons-registry",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_connected": db_ok,
        "privacy_guard_active": True,
        "max_coordinate_decimals": settings.MAX_COORDINATE_DECIMALS,
    }
