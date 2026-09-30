from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    farm_name: str = Field(..., examples=["Vidarbha Green Oasis"])
    village_district: Optional[str] = Field(None, examples=["Wardha, Vidarbha"])
    state_province: str = Field(..., examples=["Maharashtra"])
    country_code: str = Field("IND", max_length=3, examples=["IND"])
    total_area_hectares: float = Field(0.0, examples=[2.5])


class FarmCreate(FarmBase):
    pass


class FarmResponse(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime


class FieldCreate(BaseModel):
    field_name: str = Field(..., examples=["North Field - Plot A"])
    boundary_geojson: Dict[str, Any] = Field(
        ...,
        examples=[{
            "type": "Polygon",
            "coordinates": [
                [
                    [78.5833, 20.7453],
                    [78.5865, 20.7453],
                    [78.5865, 20.7480],
                    [78.5833, 20.7480],
                    [78.5833, 20.7453]
                ]
            ]
        }]
    )
    irrigation_type: str = Field("rainfed", examples=["drip"])
    current_crop: Optional[str] = Field("cotton", examples=["cotton"])
    sowing_date: Optional[date] = Field(None, examples=["2026-06-15"])
    previous_crops: List[Dict[str, Any]] = Field(
        default_factory=lambda: [{"season": "2025-kharif", "crop": "cotton"}]
    )


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    farm_id: str
    field_name: str
    boundary_geojson: Dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    area_hectares: float
    irrigation_type: str
    current_crop: Optional[str]
    sowing_date: Optional[date]
    previous_crops: List[Dict[str, Any]]
    created_at: datetime


class SatelliteMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    acquisition_date: datetime
    satellite_source: str
    cloud_coverage_percentage: float
    mean_ndvi: float
    p10_ndvi: Optional[float] = None
    p90_ndvi: Optional[float] = None
    mean_ndwi: float
    mean_evi: float
    tile_geojson: Optional[Dict[str, Any]] = None


class SoilProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    source: str
    depth_slice: str
    ph_water: float
    organic_carbon_g_kg: float
    total_nitrogen_g_kg: Optional[float] = None
    cation_exchange_capacity_cmolc_kg: Optional[float] = None
    clay_fraction_percentage: float
    sand_fraction_percentage: float
    silt_fraction_percentage: float
    texture_class: Optional[str] = None
    bulk_density_g_cm3: Optional[float] = None
    soil_health_score: int
    score_interpretation: str
    recorded_at: datetime


class WeatherRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    record_date: date
    temp_min_celsius: float
    temp_max_celsius: float
    precipitation_mm: float
    relative_humidity_pct: float
    wind_speed_kmh: Optional[float] = None
    rainfall_anomaly_pct: Optional[float] = None
    heat_stress_hours: int
    frost_risk_flag: bool
    drought_index: Optional[float] = None
    forecast_horizon_days: int
