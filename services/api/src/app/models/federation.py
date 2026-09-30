"""
KrishiNet-BRICS - Node Federation Models.
Defines Egress Audit Logs, Data Sharing Agreements, and External Inbound Tables.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class EgressAuditLog(Base):
    """
    Immutable audit log recording every payload that crosses the sovereign node boundary.
    Guarantees that 0 farmer PII, 0 cadastral boundaries, and 0 raw leaf photos leave the country.
    """
    __tablename__ = "egress_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    destination_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "registry", "peer_node"
    destination_id: Mapped[str] = mapped_column(String(128), nullable=False)   # "brics-commons-registry-01", "node-bra-01"
    scope: Mapped[str] = mapped_column(String(64), nullable=False)             # outbreak_aggregates, impact_aggregates, etc.
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)      # SHA-256 hex digest
    payload_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    passed_egress_gate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class FederationAgreement(Base):
    """
    Bilateral and Multilateral Data Sharing Agreements.
    The Egress Gate verifies an active agreement before approving outbound transboundary sync.
    """
    __tablename__ = "federation_agreements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    local_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    peer_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # or "ALL_BRICS"
    peer_country_iso: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)  # ["outbreak_aggregates", "model_exchange"]
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)  # proposed, active, revoked
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by_local_admin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signed_by_peer_admin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    terms_document_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of legal agreement
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ExternalOutbreakAggregate(Base):
    """
    Inbound outbreak aggregates received from partner BRICS nodes via the Registry.
    Stored in a segregated table so it can never be confused with local epidemiological data.
    """
    __tablename__ = "external_outbreak_aggregates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin_country_iso: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    origin_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    h3_index: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # Resolution 6
    disease_label: Mapped[str] = mapped_column(String(64), nullable=False)
    disease_name: Mapped[str] = mapped_column(String(150), nullable=False)
    reported_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_severity: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    is_spike: Mapped[bool] = mapped_column(Boolean, default=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ExternalModelCard(Base):
    """
    Inbound model cards and weights metadata published by partner BRICS nodes.
    """
    __tablename__ = "external_model_cards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    origin_country_iso: Mapped[str] = mapped_column(String(8), nullable=False)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(32), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    crop_coverage: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantization: Mapped[str] = mapped_column(String(16), default="int8")
    size_mb: Mapped[float] = mapped_column(Float, nullable=False)
    license_type: Mapped[str] = mapped_column(String(64), nullable=False)
    weights_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    download_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="candidate")  # candidate, active, rejected
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ExternalImpactMetric(Base):
    """
    Inbound macro impact figures published by other sovereign nodes.
    """
    __tablename__ = "external_impact_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin_country_iso: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    origin_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    farmers_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    hectares_regenerated: Mapped[float] = mapped_column(Float, nullable=False)
    water_saved_megalitres: Mapped[float] = mapped_column(Float, nullable=False)
    co2e_sequestered_tonnes: Mapped[float] = mapped_column(Float, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ExternalClimateSignature(Base):
    """
    Inbound climate signature vectors published by other sovereign nodes for analogue matching.
    """
    __tablename__ = "external_climate_signatures"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin_country_iso: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    origin_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    district_name: Mapped[str] = mapped_column(String(150), nullable=False)
    h3_res5_index: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)  # max 2 decimals
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)  # max 2 decimals
    monthly_tmax: Mapped[List[float]] = mapped_column(JSON, nullable=False)  # 12 months
    monthly_tmin: Mapped[List[float]] = mapped_column(JSON, nullable=False)  # 12 months
    monthly_precip: Mapped[List[float]] = mapped_column(JSON, nullable=False)  # 12 months
    aridity_index: Mapped[float] = mapped_column(Float, nullable=False)
    growing_degree_days: Mapped[float] = mapped_column(Float, nullable=False)
    soil_texture_class: Mapped[str] = mapped_column(String(64), nullable=False)
    soil_ph_band: Mapped[str] = mapped_column(String(32), nullable=False)
    proven_practices: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
