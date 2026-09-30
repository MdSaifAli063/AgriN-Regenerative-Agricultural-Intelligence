import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_token_payload
from app.models.farm import Farm, Field, SatelliteMetric, SoilProfile, WeatherRecord
from app.schemas.farm import (
    FarmCreate,
    FarmResponse,
    FieldCreate,
    FieldResponse,
    SatelliteMetricResponse,
    SoilProfileResponse,
    WeatherRecordResponse
)
from app.services.geo_utils import calculate_polygon_metrics

router = APIRouter(tags=["Farms & Fields Spatial Management"])


# ============================================================================
# FARMS
# ============================================================================
@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    farm_in: FarmCreate,
    payload: dict = Depends(get_current_user_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """Create a new farm profile."""
    user_id = payload.get("sub", "demo-farmer-id-india-001")
    farm = Farm(
        id=str(uuid.uuid4()),
        user_id=user_id,
        farm_name=farm_in.farm_name,
        village_district=farm_in.village_district,
        state_province=farm_in.state_province,
        country_code=farm_in.country_code,
        total_area_hectares=farm_in.total_area_hectares
    )
    db.add(farm)
    await db.commit()
    await db.refresh(farm)
    return FarmResponse.model_validate(farm)


@router.get("/farms", response_model=List[FarmResponse])
async def list_farms(
    payload: dict = Depends(get_current_user_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """List all farms belonging to the current user."""
    user_id = payload.get("sub", "demo-farmer-id-india-001")
    result = await db.execute(select(Farm).where(Farm.user_id == user_id))
    farms = result.scalars().all()
    
    if not farms and settings.DEMO_MODE:
        # Provide demo farm
        return [
            FarmResponse(
                id="demo-farm-india-001",
                user_id=user_id,
                farm_name="Vidarbha Regenerative Cotton Farm",
                village_district="Wardha District",
                state_province="Maharashtra",
                country_code="IND",
                total_area_hectares=2.45,
                created_at=datetime.now(timezone.utc)
            )
        ]
    return farms


@router.get("/farms/{farm_id}", response_model=FarmResponse)
async def get_farm(
    farm_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve farm details."""
    result = await db.execute(select(Farm).where(Farm.id == farm_id))
    farm = result.scalar_one_or_none()
    if not farm:
        if settings.DEMO_MODE:
            return FarmResponse(
                id=farm_id,
                user_id="demo-farmer-id-india-001",
                farm_name="Vidarbha Regenerative Cotton Farm",
                village_district="Wardha District",
                state_province="Maharashtra",
                country_code="IND",
                total_area_hectares=2.45,
                created_at=datetime.now(timezone.utc)
            )
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


# ============================================================================
# FIELDS & MAPLIBRE ONBOARDING
# ============================================================================
@router.post("/farms/{farm_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def onboard_field(
    farm_id: str,
    field_in: FieldCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Onboard a new field in under 60 seconds.
    Computes centroid and area in hectares automatically from the GeoJSON polygon.
    """
    try:
        centroid_lat, centroid_lon, area_ha = calculate_polygon_metrics(field_in.boundary_geojson)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GeoJSON polygon: {str(e)}"
        )

    field = Field(
        id=str(uuid.uuid4()),
        farm_id=farm_id,
        field_name=field_in.field_name,
        boundary_geojson=field_in.boundary_geojson,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_hectares=area_ha,
        irrigation_type=field_in.irrigation_type,
        current_crop=field_in.current_crop,
        sowing_date=field_in.sowing_date,
        previous_crops=field_in.previous_crops
    )

    db.add(field)

    # Automatically generate initial baseline environmental records for demo mode
    if settings.DEMO_MODE:
        # 1. Baseline Soil Profile
        soil = SoilProfile(
            field_id=field.id,
            source="ISRIC SoilGrids 250m v2.0",
            depth_slice="0-30cm",
            ph_water=7.4,
            organic_carbon_g_kg=6.8,
            total_nitrogen_g_kg=0.85,
            cation_exchange_capacity_cmolc_kg=38.5,
            clay_fraction_percentage=54.0,
            sand_fraction_percentage=18.0,
            silt_fraction_percentage=28.0,
            texture_class="clay",
            bulk_density_g_cm3=1.35,
            soil_health_score=68,
            score_interpretation="Moderate Health (Vertisol/Black Cotton Soil). High moisture retention; needs organic carbon enrichment and cover cropping."
        )
        db.add(soil)

        # 2. Baseline Satellite Metric (Sentinel-2)
        sat = SatelliteMetric(
            field_id=field.id,
            acquisition_date=datetime.now(timezone.utc) - timedelta(days=2),
            satellite_source="Sentinel-2 L2A",
            cloud_coverage_percentage=4.2,
            mean_ndvi=0.62,
            p10_ndvi=0.48,
            p90_ndvi=0.74,
            mean_ndwi=0.18,
            mean_evi=0.45,
            tile_geojson={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": field_in.boundary_geojson,
                        "properties": {"ndvi": 0.62, "status": "healthy_vegetation"}
                    }
                ]
            }
        )
        db.add(sat)

    await db.commit()
    await db.refresh(field)
    return FieldResponse.model_validate(field)


@router.get("/farms/{farm_id}/fields", response_model=List[FieldResponse])
async def list_fields(
    farm_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all spatial fields in a farm."""
    result = await db.execute(select(Field).where(Field.farm_id == farm_id))
    fields = result.scalars().all()
    if not fields and settings.DEMO_MODE:
        return [
            FieldResponse(
                id="demo-field-india-001",
                farm_id=farm_id,
                field_name="Plot 1 - Vidarbha Cotton Field",
                boundary_geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.5833, 20.7453],
                            [78.5880, 20.7453],
                            [78.5880, 20.7490],
                            [78.5833, 20.7490],
                            [78.5833, 20.7453]
                        ]
                    ]
                },
                centroid_lat=20.7471,
                centroid_lon=78.5856,
                area_hectares=2.15,
                irrigation_type="drip",
                current_crop="cotton",
                sowing_date=date(2026, 6, 18),
                previous_crops=[{"season": "2025-kharif", "crop": "cotton"}, {"season": "2024-rabi", "crop": "chickpea"}],
                created_at=datetime.now(timezone.utc)
            )
        ]
    return fields


@router.get("/fields/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get field spatial and crop details."""
    result = await db.execute(select(Field).where(Field.id == field_id))
    field = result.scalar_one_or_none()
    if not field:
        if settings.DEMO_MODE:
            return FieldResponse(
                id=field_id,
                farm_id="demo-farm-india-001",
                field_name="Plot 1 - Vidarbha Cotton Field",
                boundary_geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.5833, 20.7453],
                            [78.5880, 20.7453],
                            [78.5880, 20.7490],
                            [78.5833, 20.7490],
                            [78.5833, 20.7453]
                        ]
                    ]
                },
                centroid_lat=20.7471,
                centroid_lon=78.5856,
                area_hectares=2.15,
                irrigation_type="drip",
                current_crop="cotton",
                sowing_date=date(2026, 6, 18),
                previous_crops=[{"season": "2025-kharif", "crop": "cotton"}],
                created_at=datetime.now(timezone.utc)
            )
        raise HTTPException(status_code=404, detail="Field not found")
    return field


# ============================================================================
# SATELLITE, SOIL & WEATHER TELEMETRY
# ============================================================================
@router.get("/fields/{field_id}/satellite", response_model=List[SatelliteMetricResponse])
async def get_satellite_timeseries(
    field_id: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve 90-day NDVI/NDWI/EVI Sentinel-2 timeseries."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(SatelliteMetric)
        .where(SatelliteMetric.field_id == field_id, SatelliteMetric.acquisition_date >= cutoff)
        .order_by(SatelliteMetric.acquisition_date.asc())
    )
    records = result.scalars().all()
    
    if not records and settings.DEMO_MODE:
        # Generate realistic 90-day Sentinel-2 NDVI trend
        demo_series = []
        base_date = datetime.now(timezone.utc) - timedelta(days=90)
        ndvi_values = [0.22, 0.28, 0.35, 0.44, 0.53, 0.61, 0.68, 0.65, 0.63, 0.60]
        for i, val in enumerate(ndvi_values):
            acq_date = base_date + timedelta(days=i * 9)
            demo_series.append(
                SatelliteMetricResponse(
                    id=f"demo-sat-{i}",
                    field_id=field_id,
                    acquisition_date=acq_date,
                    satellite_source="Sentinel-2 L2A",
                    cloud_coverage_percentage=round(2.0 + (i % 4) * 3.1, 1),
                    mean_ndvi=val,
                    p10_ndvi=round(val - 0.08, 2),
                    p90_ndvi=round(val + 0.07, 2),
                    mean_ndwi=round(val * 0.45 - 0.1, 2),
                    mean_evi=round(val * 0.75, 2),
                    tile_geojson=None
                )
            )
        return demo_series

    return records


@router.get("/fields/{field_id}/soil", response_model=SoilProfileResponse)
async def get_soil_profile(
    field_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve ISRIC SoilGrids profile and Soil Health Score."""
    result = await db.execute(
        select(SoilProfile).where(SoilProfile.field_id == field_id).order_by(SoilProfile.recorded_at.desc())
    )
    soil = result.scalar_one_or_none()
    
    if not soil and settings.DEMO_MODE:
        return SoilProfileResponse(
            id="demo-soil-001",
            field_id=field_id,
            source="ISRIC SoilGrids 250m v2.0",
            depth_slice="0-30cm",
            ph_water=7.4,
            organic_carbon_g_kg=6.8,
            total_nitrogen_g_kg=0.85,
            cation_exchange_capacity_cmolc_kg=38.5,
            clay_fraction_percentage=54.0,
            sand_fraction_percentage=18.0,
            silt_fraction_percentage=28.0,
            texture_class="clay",
            bulk_density_g_cm3=1.35,
            soil_health_score=68,
            score_interpretation="Moderate Health (Vertisol/Black Cotton Soil). High moisture retention; needs organic carbon enrichment and cover cropping.",
            recorded_at=datetime.now(timezone.utc)
        )
    if not soil:
        raise HTTPException(status_code=404, detail="Soil profile not found")
    return soil


@router.get("/fields/{field_id}/weather", response_model=List[WeatherRecordResponse])
async def get_weather_forecast(
    field_id: str,
    horizon_days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve 7-day agro-climatic forecast and stress risks."""
    result = await db.execute(
        select(WeatherRecord)
        .where(WeatherRecord.field_id == field_id)
        .order_by(WeatherRecord.record_date.asc())
        .limit(horizon_days)
    )
    records = result.scalars().all()
    
    if not records and settings.DEMO_MODE:
        demo_weather = []
        today = date.today()
        for d in range(horizon_days):
            day_date = today + timedelta(days=d)
            demo_weather.append(
                WeatherRecordResponse(
                    id=f"demo-weather-{d}",
                    field_id=field_id,
                    record_date=day_date,
                    temp_min_celsius=24.5 + (d % 2),
                    temp_max_celsius=33.8 + (d % 3),
                    precipitation_mm=4.5 if d in [1, 2] else 0.0,
                    relative_humidity_pct=68.0 - (d * 2),
                    wind_speed_kmh=12.5,
                    rainfall_anomaly_pct=-14.2,
                    heat_stress_hours=2 if d > 3 else 0,
                    frost_risk_flag=False,
                    drought_index=0.18,
                    forecast_horizon_days=7
                )
            )
        return demo_weather

    return records
