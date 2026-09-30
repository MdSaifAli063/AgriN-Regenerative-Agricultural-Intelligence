"""
KrishiNet-BRICS – Disease Diagnostic API Schemas (Pydantic v2).

Request/response contracts for:
  POST /disease/diagnose          – image upload + diagnosis
  GET  /disease/detections/{id}   – single detection retrieval
  GET  /disease/outbreak/feed     – GeoJSON outbreak feed
  GET  /disease/outbreak/feed.jsonld – JSON-LD outbreak feed
  POST /disease/offline/sync      – offline batch sync endpoint
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class Top3PredictionOut(BaseModel):
    label: str
    confidence: float
    canonical_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Diagnosis request/response
# ---------------------------------------------------------------------------

class DiagnoseRequest(BaseModel):
    """
    Optional metadata accompanying an image upload.
    The image itself is sent as multipart/form-data.
    """
    field_id: Optional[str] = Field(None, description="Field UUID (optional)")
    crop_hint: Optional[str] = Field(None, max_length=100, description="Crop name hint (e.g. 'rice')")
    latitude: float = Field(0.0, ge=-90.0, le=90.0)
    longitude: float = Field(0.0, ge=-180.0, le=180.0)
    language: str = Field("en", max_length=10, description="ISO 639-1 language code for response localisation")


class DiagnoseResponse(BaseModel):
    """Full disease diagnosis report returned to the client."""
    detection_id: str
    primary_disease_name: str
    primary_disease_label: str
    canonical_name: str
    fao_agrovoc_uri: Optional[str] = None

    severity_level: str
    spread_risk_score: str

    top_3_predictions: List[Top3PredictionOut]
    ensemble_confidence: float

    organic_treatment: str
    chemical_treatment: Optional[str] = None
    chemical_safety_warning: Optional[str] = None
    prevention_measures: List[str]

    weather_risk_amplified: bool
    weather_risk_factors: List[str]

    visual_reasoning: str
    is_healthy: bool

    confidence_sufficient: bool
    confidence_warning: Optional[str] = None

    # Explainability / provenance
    fusion_strategy: str
    edge_weight: float
    gemini_weight: float
    ood_rejected: bool
    model_version: str

    image_s3_uri: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Detection retrieval
# ---------------------------------------------------------------------------

class DetectionHistoryItem(BaseModel):
    """Compact list item for a farmer's detection history."""
    id: str
    primary_disease_name: str
    severity_level: str
    spread_risk_score: str
    ensemble_confidence: float
    image_s3_uri: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Offline sync
# ---------------------------------------------------------------------------

class OfflineSyncItem(BaseModel):
    """Single offline detection queued while the device was offline."""
    client_id: str = Field(..., description="Client-generated UUID for idempotency")
    image_s3_uri: str = Field(..., description="MinIO URI where the client already uploaded the image")
    field_id: Optional[str] = None
    crop_hint: Optional[str] = None
    latitude: float = Field(0.0, ge=-90.0, le=90.0)
    longitude: float = Field(0.0, ge=-180.0, le=180.0)
    captured_at: Optional[datetime] = None
    language: str = "en"

    @field_validator("image_s3_uri")
    @classmethod
    def must_have_scheme(cls, v: str) -> str:
        if not v.startswith(("s3://", "minio://", "http://", "https://")):
            raise ValueError("image_s3_uri must begin with s3://, minio://, http://, or https://")
        return v


class OfflineSyncRequest(BaseModel):
    items: List[OfflineSyncItem] = Field(..., max_length=50, description="Batch of queued detections (max 50)")


class OfflineSyncResultItem(BaseModel):
    client_id: str
    status: str          # "ok" | "error" | "skipped"
    detection_id: Optional[str] = None
    primary_disease_name: Optional[str] = None
    error: Optional[str] = None


class OfflineSyncResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: List[OfflineSyncResultItem]


# ---------------------------------------------------------------------------
# Outbreak feed metadata wrapper
# ---------------------------------------------------------------------------

class OutbreakFeedParams(BaseModel):
    """Query parameters for the outbreak feed endpoint."""
    country_iso: Optional[str] = Field(None, max_length=3)
    disease_name: Optional[str] = Field(None, max_length=150)
    risk_severity: Optional[str] = Field(None, pattern=r"^(low|moderate|high|severe)$")
    since_days: int = Field(30, ge=1, le=365, description="Look back N days")
    limit: int = Field(200, ge=1, le=500)
    format: str = Field("geojson", pattern=r"^(geojson|jsonld)$")
