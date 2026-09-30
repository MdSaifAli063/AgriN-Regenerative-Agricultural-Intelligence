from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FarmBase(BaseModel):
    farm_name: str = Field(..., min_length=2, max_length=255, examples=["Vidarbha Regenerative Cotton Farm"])
    village_district: Optional[str] = Field(None, max_length=255, examples=["Wardha"])
    state_province: str = Field(..., min_length=2, max_length=255, examples=["Maharashtra"])
    country_iso: str = Field("IND", min_length=2, max_length=3, examples=["IND"])
    total_area_hectares: float = Field(0.0, ge=0.0, examples=[2.45])


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    farm_name: Optional[str] = None
    village_district: Optional[str] = None
    state_province: Optional[str] = None
    total_area_hectares: Optional[float] = None


class FarmResponse(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime


class FieldCreate(BaseModel):
    field_name: str = Field(..., min_length=2, max_length=100, examples=["Parcel 1 - Main Field"])
    boundary_geojson: Dict[str, Any] = Field(
        ...,
        examples=[{
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
        }],
    )
    irrigation_type: str = Field("rainfed", examples=["rainfed", "drip", "sprinkler", "furrow"])
    current_crop: Optional[str] = Field(None, examples=["cotton"])
    sowing_date: Optional[date] = Field(None, examples=["2026-06-15"])


class FieldFromPointRequest(BaseModel):
    field_name: str = Field("Pin Field", min_length=2, max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0, examples=[20.7471])
    longitude: float = Field(..., ge=-180.0, le=180.0, examples=[78.5856])
    side_meters: float = Field(100.0, ge=10.0, le=2000.0, description="Square side length in meters (default 100m = 1 ha)")
    irrigation_type: str = Field("rainfed", examples=["rainfed", "drip"])
    current_crop: Optional[str] = Field("cotton", examples=["cotton"])


class FieldUpdate(BaseModel):
    field_name: Optional[str] = None
    irrigation_type: Optional[str] = None
    current_crop: Optional[str] = None
    sowing_date: Optional[date] = None


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
    current_crop: Optional[str] = None
    sowing_date: Optional[date] = None
    created_at: datetime


class CropHistoryCreate(BaseModel):
    crop_name: str = Field(..., examples=["Cotton"])
    fao_agrovoc_uri: Optional[str] = Field(None, examples=["http://aims.fao.org/aos/agrovoc/c_1940"])
    season_name: str = Field(..., examples=["kharif_2025"])
    sowing_date: Optional[date] = None
    harvest_date: Optional[date] = None
    yield_kg_ha: Optional[float] = None
    fertilizers_applied: List[Dict[str, Any]] = Field(default_factory=list)


class CropHistoryResponse(CropHistoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    created_at: datetime


class OnboardingRequest(BaseModel):
    full_name: str = Field(..., examples=["Ramesh Patil"])
    phone_number: str = Field(..., examples=["+919876543210"])
    country_iso: str = Field("IND", min_length=2, max_length=3, examples=["IND"])
    preferred_language: str = Field("hi", examples=["hi"])
    farm_name: str = Field(..., examples=["Vidarbha Cotton Parcel"])
    state_province: str = Field(..., examples=["Maharashtra"])
    village_district: Optional[str] = Field("Wardha", examples=["Wardha"])
    field_name: str = Field("Main Field", examples=["Main Field"])
    boundary_geojson: Dict[str, Any]
    current_crop: str = Field("cotton", examples=["cotton"])
    irrigation_type: str = Field("rainfed", examples=["rainfed", "drip"])
    share_anonymized_soil: bool = True
    share_outbreak_telemetry: bool = True
    participate_in_federated_learning: bool = True


class OnboardingResponse(BaseModel):
    user_id: str
    farm_id: str
    field_id: str
    area_hectares: float
    access_token: str
    message: str = "Onboarding completed successfully in one transaction."
