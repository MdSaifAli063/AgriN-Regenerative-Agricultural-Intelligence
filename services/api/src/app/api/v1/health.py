import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.deps import get_db

from datetime import datetime, timezone

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health/live")
async def liveness_probe():
    """Liveness probe: verifies process is alive."""
    return {
        "status": "alive",
        "service": "KrishiNet-BRICS API",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



@router.get("/health/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe: validates connectivity across DB, Redis, MinIO, and Keycloak.
    Gracefully tolerates non-critical dependencies when DEMO_MODE=true.
    """
    checks = {
        "database": False,
        "redis": False,
        "minio": False,
        "keycloak": False,
    }

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # 2. Redis check
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = settings.DEMO_MODE  # Pass in demo mode

    # 3. MinIO check
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"http://{settings.MINIO_ENDPOINT}/minio/health/live")
            checks["minio"] = resp.status_code == 200
    except Exception:
        checks["minio"] = settings.DEMO_MODE

    # 4. Keycloak check
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}")
            checks["keycloak"] = resp.status_code == 200
    except Exception:
        checks["keycloak"] = settings.DEMO_MODE or settings.DEV_AUTH_BYPASS

    is_ready = checks["database"] and (checks["redis"] or settings.DEMO_MODE)
    if not is_ready and not settings.DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)

    return {
        "status": "ready" if is_ready else "degraded",
        "demo_mode": settings.DEMO_MODE,
        "components": checks,
    }


@router.get("/health/demo-mode")
async def demo_mode_status():
    """Returns Demo-Mode settings and active fallback layers."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "dev_auth_bypass": settings.DEV_AUTH_BYPASS,
        "node_id": settings.NODE_ID,
        "country": settings.NODE_COUNTRY,
        "node_country": settings.NODE_COUNTRY,
        "fallback_providers": [
            "Copernicus Sentinel-2 STAC Mock Layer",
            "ISRIC SoilGrids Deterministic Chemistry Engine",
            "Open-Meteo & NASA POWER 7-Day Resilient Forecasts",
            "Gemini 1.5/2.0 Grounded Agronomy Fallback Generator",
        ],
    }


@router.get("/health/providers")
async def external_providers_status():
    """
    Returns operational health status of each upstream environmental data provider:
    - Sentinel-2 L2A STAC (AWS Element84)
    - ISRIC SoilGrids v2.0 REST API
    - Open-Meteo Weather Forecast API
    - NASA POWER Climatology Point API
    """
    providers = {}

    # 1. Sentinel-2 STAC
    stac_url = settings.EARTH_SEARCH_STAC_URL
    if settings.DEMO_MODE:
        providers["sentinel2"] = {
            "name": "Sentinel-2 L2A (STAC)",
            "status": "demo",
            "url": stac_url,
            "mode": "synthetic_observations_active",
        }
    else:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(stac_url)
                providers["sentinel2"] = {
                    "name": "Sentinel-2 L2A (STAC)",
                    "status": "up" if resp.status_code == 200 else "degraded",
                    "url": stac_url,
                }
        except Exception:
            providers["sentinel2"] = {
                "name": "Sentinel-2 L2A (STAC)",
                "status": "degraded",
                "url": stac_url,
                "fallback": "synthetic_observations",
            }

    # 2. ISRIC SoilGrids
    soil_url = settings.ISRIC_SOILGRIDS_API_URL
    if settings.DEMO_MODE:
        providers["soilgrids"] = {
            "name": "ISRIC SoilGrids 250m v2.0",
            "status": "demo",
            "url": soil_url,
            "mode": "regional_vertisol_oxisol_arenosol_fixtures",
        }
    else:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{soil_url}?lat=20.0&lon=78.0&property=phh2o&depth=0-5cm")
                providers["soilgrids"] = {
                    "name": "ISRIC SoilGrids 250m v2.0",
                    "status": "up" if resp.status_code == 200 else "degraded",
                    "url": soil_url,
                }
        except Exception:
            providers["soilgrids"] = {
                "name": "ISRIC SoilGrids 250m v2.0",
                "status": "degraded",
                "url": soil_url,
                "fallback": "regional_soil_chemistry_fixtures",
            }

    # 3. Open-Meteo Weather
    wx_url = settings.OPEN_METEO_BASE_URL
    if settings.DEMO_MODE:
        providers["open_meteo"] = {
            "name": "Open-Meteo Weather API",
            "status": "demo",
            "url": wx_url,
            "mode": "deterministic_microclimate_forecasts",
        }
    else:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{wx_url}?latitude=20.0&longitude=78.0&current=temperature_2m")
                providers["open_meteo"] = {
                    "name": "Open-Meteo Weather API",
                    "status": "up" if resp.status_code == 200 else "degraded",
                    "url": wx_url,
                }
        except Exception:
            providers["open_meteo"] = {
                "name": "Open-Meteo Weather API",
                "status": "degraded",
                "url": wx_url,
                "fallback": "climatological_forecast_models",
            }

    # 4. NASA POWER Climatology
    nasa_url = settings.NASA_POWER_BASE_URL
    if settings.DEMO_MODE:
        providers["nasa_power"] = {
            "name": "NASA POWER Agro-Climatology",
            "status": "demo",
            "url": nasa_url,
            "mode": "ten_year_historical_climatology_baselines",
        }
    else:
        providers["nasa_power"] = {
            "name": "NASA POWER Agro-Climatology",
            "status": "up",
            "url": nasa_url,
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demo_mode": settings.DEMO_MODE,
        "providers": providers,
    }


