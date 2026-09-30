"""
Part 7D – Model Hub Database Models.

Adds promotion-gate tracking, Ed25519 signed model card artifacts,
and evaluation result records to the existing MLModel / ModelCard tables.
New tables (no changes to Phase 1 schema):
  - ModelHubEntry        : Hub catalog entry per promoted model version
  - ModelEvaluation      : Evaluation run results (accuracy, fairness, provenance)
  - ModelPromotionEvent  : Immutable audit trail of promote / reject decisions
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ModelHubEntry(Base):
    """
    A single promoted-and-signed model version available in the Hub catalog.
    The Hub is the single source of truth for which model versions are
    cleared for download and edge deployment across BRICS nodes.
    """
    __tablename__ = "model_hub_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # FK to the Phase-1 ModelCard
    model_card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_cards.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    country_iso: Mapped[str] = mapped_column(String(8), nullable=False)
    # Hub lifecycle state
    status: Mapped[str] = mapped_column(
        String(32), default="candidate", nullable=False, index=True
    )  # candidate | promoted | deprecated | rejected
    # Weights artifact reference (MinIO)
    bucket: Mapped[str] = mapped_column(String(150), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)  # e.g. models/<id>/weights.tflite
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    weights_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Ed25519 card signature (node signs the card_json bytes)
    card_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    card_signature_hex: Mapped[str] = mapped_column(String(128), nullable=False)   # hex(Ed25519 sig)
    card_signed_by_node: Mapped[str] = mapped_column(String(64), nullable=False)   # node_id that signed
    # Metadata
    quantization: Mapped[str] = mapped_column(String(16), default="int8")
    framework: Mapped[str] = mapped_column(String(32), default="tflite")  # tflite | onnx | pytorch
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    crop_coverage: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    license_type: Mapped[str] = mapped_column(String(64), default="Apache-2.0")
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    evaluations: Mapped[List["ModelEvaluation"]] = relationship(
        "ModelEvaluation", back_populates="hub_entry", cascade="all, delete-orphan"
    )
    promotion_events: Mapped[List["ModelPromotionEvent"]] = relationship(
        "ModelPromotionEvent", back_populates="hub_entry", cascade="all, delete-orphan"
    )


class ModelEvaluation(Base):
    """
    Results of a structured evaluation run against the standard
    KrishiNet-BRICS eval harness (held-out test set per crop-country pair).
    """
    __tablename__ = "model_evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    hub_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_hub_entries.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    eval_dataset: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. "IND-wheat-holdout-v3"
    eval_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Core metrics
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    f1_macro: Mapped[float] = mapped_column(Float, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    # Fairness metrics (per-crop subgroup equity)
    min_subgroup_f1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_demographic_parity_gap: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fairness_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Edge performance
    inference_ms_p50: Mapped[float] = mapped_column(Float, nullable=True)   # median latency ms
    inference_ms_p95: Mapped[float] = mapped_column(Float, nullable=True)   # p95 latency ms
    peak_ram_mb: Mapped[float] = mapped_column(Float, nullable=True)        # peak RAM MB on edge device
    # Promotion gate pass/fail
    gate_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gate_detail: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # Provenance
    eval_commit_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    hub_entry: Mapped["ModelHubEntry"] = relationship("ModelHubEntry", back_populates="evaluations")


class ModelPromotionEvent(Base):
    """
    Immutable audit trail every time a model is promoted, deprecated, or rejected.
    Signed by the reviewer's node identity key.
    """
    __tablename__ = "model_promotion_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    hub_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_hub_entries.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # promote | reject | deprecate | withdraw
    reviewer_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_country_iso: Mapped[str] = mapped_column(String(8), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    signature_hex: Mapped[str] = mapped_column(String(128), nullable=False)   # Ed25519 over event JSON
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    hub_entry: Mapped["ModelHubEntry"] = relationship("ModelHubEntry", back_populates="promotion_events")
