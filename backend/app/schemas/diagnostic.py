from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DiagnosticPrediction(BaseModel):
    disease_name: str
    scientific_name: Optional[str] = None
    confidence: float
    fao_agrovoc_uri: Optional[str] = None


class DiseaseDiagnosticResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    primary_disease_name: str
    fao_agrovoc_disease_uri: Optional[str] = None
    severity_rating: str
    confidence: float
    top_predictions: List[Dict[str, Any]]
    organic_treatment: str
    chemical_treatment: Optional[str] = None
    chemical_safety_warning: Optional[str] = None
    prevention_measures: List[str]
    spread_risk_level: str
    weather_risk_factors: Dict[str, Any]
    image_url: str
    created_at: datetime


class OutbreakFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class OutbreakCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[OutbreakFeature]
