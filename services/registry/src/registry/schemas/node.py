"""
BRICS Commons Registry - Pydantic Schemas for Node Handshakes and Heartbeats.
Enforces extra="forbid" on all inbound schemas to prevent PII injection.
"""

import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class NodeRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    country_code: str = Field(..., min_length=2, max_length=3)
    organisation_name: str = Field(..., min_length=2, max_length=255)
    public_key: str = Field(..., min_length=32, max_length=128, description="Base64 encoded 32-byte Ed25519 public key")
    capabilities: List[str] = Field(default_factory=list)
    api_base_url: str = Field(..., min_length=8, max_length=512)
    version: str = Field(default="1.0.0", max_length=32)
    contact_email: str = Field(..., max_length=255)
    registration_signature: Optional[str] = Field(None, description="Optional Ed25519 signature of the registration payload")


class NodeRegistrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    country_code: str
    organisation_name: str
    status: Literal["pending", "approved", "suspended", "revoked"]
    registered_at: datetime.datetime
    message: str


class NodeStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = Field(None, max_length=255)


class AggregateCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farmers_active: int = Field(0, ge=0)
    hectares_regenerated: int = Field(0, ge=0)
    water_saved_ml: int = Field(0, ge=0)
    co2e_sequestered_tonnes: int = Field(0, ge=0)
    validated_detections: int = Field(0, ge=0)
    outbreaks_reported: int = Field(0, ge=0)


class NodeHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded"]
    api_version: str = Field(..., max_length=32)
    active_models: List[str] = Field(default_factory=list)
    aggregate_counts: AggregateCounts


class NodeHeartbeatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    status: str
    last_heartbeat_at: datetime.datetime
    is_stale: bool
    acknowledged: bool = True


class KeyRotationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_public_key: str = Field(..., min_length=32, max_length=128)
    key_version: int = Field(..., ge=2)


class KeyRotationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    key_version: int
    grace_period_expires_at: datetime.datetime
    message: str


class NodeKeySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    public_key: str
    key_version: int
    status: str
    valid_from: datetime.datetime
    expires_at: Optional[datetime.datetime]


class NodeDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    country_code: str
    organisation_name: str
    status: Literal["pending", "approved", "suspended", "revoked"]
    api_base_url: str
    capabilities: List[str]
    version: str
    contact_email: str
    registered_at: datetime.datetime
    approved_at: Optional[datetime.datetime]
    last_heartbeat_at: Optional[datetime.datetime]
    is_stale: bool
    active_key: Optional[str]
    keys: List[NodeKeySummary] = Field(default_factory=list)
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
