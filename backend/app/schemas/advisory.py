from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RegenerativePractice(BaseModel):
    practice_name: str
    fao_category: str
    description: str
    cost_level: str
    soil_benefit: str
    carbon_benefit: str
    implementation_steps: List[str]


class CropRecommendation(BaseModel):
    crop_name: str
    scientific_name: Optional[str] = None
    suitability_score: float
    expected_yield_range: str
    water_need_mm: int
    climate_risk_rating: str
    market_demand: Optional[str] = None


class AdvisoryGenerateRequest(BaseModel):
    field_id: str
    preferred_language: str = "en"
    target_season: Optional[str] = "upcoming"


class AdvisoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_id: str
    confidence_score: float
    hallucination_guard_passed: bool
    top_crop_recommendations: List[Dict[str, Any]]
    regenerative_practices: List[Dict[str, Any]]
    sowing_window: Dict[str, Any]
    irrigation_schedule: Dict[str, Any]
    organic_fertilizer_plan: Dict[str, Any]
    action_calendar_30days: List[Dict[str, Any]]
    data_signals_cited: Dict[str, Any]
    carbon_sequestration_est_t_ha: Optional[float] = None
    water_conservation_est_pct: Optional[int] = None
    yield_uplift_est_pct: Optional[int] = None
    disclaimer_notice: str
    created_at: datetime
