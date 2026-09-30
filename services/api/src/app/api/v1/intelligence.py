"""
KrishiNet-BRICS - Field Intelligence API Endpoints.

Provides REST endpoints for:
  - Combined real-time Field Intelligence Snapshot (Satellite + Soil + Weather + Soil Health Score)
  - Sentinel-2 Satellite Vegetation Indices (90-day time series, PNG raster overlay, GeoJSON grid)
  - MapLibre raster tiles bounds and legend
  - ISRIC SoilGrids Physical-Chemical Analysis & Soil Health Score
  - Open-Meteo & NASA POWER 7-Day Micro-Climate & Agro-Hazards
  - Asynchronous background refresh trigger (202 Accepted)
  - Public crop thermal thresholds & FAO-56 crop coefficients
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.core.security import check_farm_ownership, get_current_user
from app.models.farm import Farm, Field
from app.models.user import User
from app.repositories.farm_repo import FarmRepository, FieldRepository
from app.services.intel.orchestrator import field_intelligence_service
from app.services.intel.satellite_service import satellite_service
from app.services.intel.soil_service import soil_service
from app.services.intel.weather_service import (
    CROP_HEAT_THRESHOLDS,
    CROP_KC_VALUES,
    weather_service,
)

logger = logging.getLogger("krishinet.api.intelligence")

router = APIRouter(tags=["Field Environmental Intelligence"])


async def _get_field_and_authorize(
    field_id: str,
    current_user: User,
    db: AsyncSession,
) -> Field:
    """Helper to fetch Field, verify existence, and enforce sovereign RBAC ownership."""
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(field.farm_id)
    if farm:
        check_farm_ownership(current_user, farm, require_write=False)

    return field


# ============================================================================
# 1. COMBINED FIELD INTELLIGENCE SNAPSHOT
# ============================================================================

@router.get("/fields/{field_id}/intelligence")
async def get_field_intelligence(
    field_id: str,
    refresh: bool = Query(False, description="Bypass cache and force upstream refresh"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns consolidated sovereign real-time intelligence for an agricultural field:
    - Sentinel-2 vegetation vigor & 90-day trajectory
    - ISRIC SoilGrids 250m properties & 0-100 Soil Health Score
    - 7-Day weather forecast & multi-hazard climate indicators
    - Overall Field Health Status traffic light (healthy / watch / risk) with driving factors
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    snapshot = await field_intelligence_service.get_snapshot(
        field_id=field.id,
        db=db,
        force_refresh=refresh,
    )
    return snapshot


# ============================================================================
# 2. SATELLITE VEGETATION INTELLIGENCE
# ============================================================================

@router.get("/fields/{field_id}/satellite")
async def get_field_satellite(
    field_id: str,
    days_window: int = Query(90, ge=30, le=180, description="Observation time window in days"),
    refresh: bool = Query(False, description="Force refresh from STAC catalog"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns Sentinel-2 L2A observations:
    - 90-day time series of NDVI, NDWI, EVI, NDMI zonal statistics
    - Latest scene raster heatmap rendered with KrishiNet design ramp
    - Interactive GeoJSON vector grid (~30m cells)
    - 30-day slope trend & 90-day baseline anomaly
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    return await satellite_service.fetch(
        centroid_lat=field.centroid_lat,
        centroid_lon=field.centroid_lon,
        polygon_geojson=field.boundary_geojson,
        field_id=field.id,
        days_window=days_window,
        force_refresh=refresh,
    )


@router.get("/fields/{field_id}/satellite/tiles-info")
async def get_field_satellite_tiles_info(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns MapLibre GL JS / Leaflet tile overlay metadata:
    - Image URL of the color-mapped NDVI raster in MinIO
    - MapLibre bounding coordinates [[W, N], [E, N], [E, S], [W, S]]
    - Standard bounding box [W, S, E, N]
    - Visual legend matching design tokens
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    sat_data = await satellite_service.fetch(
        centroid_lat=field.centroid_lat,
        centroid_lon=field.centroid_lon,
        polygon_geojson=field.boundary_geojson,
        field_id=field.id,
        force_refresh=False,
    )

    overlay = sat_data.get("raster_overlay", {})
    return {
        "field_id": field.id,
        "image_url": overlay.get("image_url"),
        "bbox": overlay.get("bbox"),
        "maplibre_coordinates": overlay.get("maplibre_coordinates"),
        "legend": overlay.get("legend"),
    }


# ============================================================================
# 3. SOIL INTELLIGENCE & SOIL HEALTH SCORE
# ============================================================================

@router.get("/fields/{field_id}/soil")
async def get_field_soil(
    field_id: str,
    refresh: bool = Query(False, description="Force refresh from ISRIC SoilGrids API"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns ISRIC SoilGrids 250m soil profile:
    - Physical and chemical properties across 0-5cm, 5-15cm, 15-30cm
    - Depth-weighted 0-30cm rhizosphere profile with USDA texture triangle class
    - 0-100 Soil Health Score with component pills, top 3 limiting factors,
      and organic-first regenerative improvement hints
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    return await soil_service.fetch(
        centroid_lat=field.centroid_lat,
        centroid_lon=field.centroid_lon,
        crop=field.current_crop,
        force_refresh=refresh,
    )


# ============================================================================
# 4. WEATHER & CLIMATE HAZARDS
# ============================================================================

@router.get("/fields/{field_id}/weather")
async def get_field_weather(
    field_id: str,
    refresh: bool = Query(False, description="Force refresh from Open-Meteo API"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns Open-Meteo & NASA POWER climate telemetry:
    - Current conditions & 7-day daily forecast
    - 48-hour hourly microclimate predictions
    - Derived indicators: rainfall anomaly vs 10-year climatology, heat stress days,
      frost risk severity, drought SPI & UNEP aridity ratio, fungal disease risk score,
      FAO-56 net irrigation deficit, and low-wind spray windows
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    return await weather_service.fetch(
        centroid_lat=field.centroid_lat,
        centroid_lon=field.centroid_lon,
        crop=field.current_crop,
        force_refresh=refresh,
    )


# ============================================================================
# 5. ASYNCHRONOUS REFRESH TRIGGER
# ============================================================================

@router.post("/fields/{field_id}/intelligence/refresh", status_code=status.HTTP_202_ACCEPTED)
async def trigger_intelligence_refresh(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Asynchronously queues background telemetry refresh job in Celery worker.
    Returns HTTP 202 Accepted with worker task id.
    """
    field = await _get_field_and_authorize(field_id, current_user, db)

    task_id = field_intelligence_service.trigger_background_refresh(field.id)

    return {
        "status": "accepted",
        "task_id": task_id,
        "field_id": field.id,
        "message": "Field intelligence refresh queued in background worker.",
    }


# ============================================================================
# 6. PUBLIC CROP THRESHOLDS CONFIGURATION
# ============================================================================

@router.get("/intelligence/crop-thresholds")
async def get_crop_thresholds() -> Dict[str, Any]:
    """
    Public registry of agronomic crop thermal thresholds and FAO-56 crop coefficients
    utilized across BRICS sovereign agricultural intelligence nodes.
    """
    descriptions = {
        "cotton": "Gossypium hirsutum - Tolerant up to 38°C; high sensitivity during flowering/boll formation.",
        "soybean": "Glycine max - Thermal threshold 35°C; elevated Asian rust risk above 75% RH.",
        "maize": "Zea mays - Optimal 25-32°C; heat above 35°C impairs pollen viability and silk elongation.",
        "wheat": "Triticum aestivum - Cool-season cereal; terminal heat stress occurs above 30°C.",
        "rice": "Oryza sativa - Thermal ceiling 36°C; susceptible to floret sterility during anthesis.",
        "sorghum": "Sorghum bicolor - High drought and heat resilience up to 40°C.",
        "millet": "Pennisetum glaucum - Arid-adapted cereal tolerant up to 42°C.",
        "pulses": "Grain legumes (pigeonpea, chickpea, cowpea) - Thermal stress begins above 35°C.",
    }

    crops_payload = {}
    for crop_name, thresh in CROP_HEAT_THRESHOLDS.items():
        crops_payload[crop_name] = {
            "heat_stress_threshold_celsius": thresh,
            "fao_crop_coefficient_kc": CROP_KC_VALUES.get(crop_name, 1.0),
            "agronomic_notes": descriptions.get(crop_name, "Standard crop coefficient baseline."),
        }

    return {
        "total_crops": len(crops_payload),
        "crops": crops_payload,
    }
