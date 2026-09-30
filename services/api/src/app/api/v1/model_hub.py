"""
Part 7D – Model Hub API Endpoints.

Routes:
  GET  /api/v1/model-hub/                          → List Hub catalog
  POST /api/v1/model-hub/                          → Register new candidate entry
  GET  /api/v1/model-hub/{entry_id}                → Get entry detail
  GET  /api/v1/model-hub/{entry_id}/download-url   → Presigned MinIO download URL
  POST /api/v1/model-hub/{entry_id}/evaluations    → Submit evaluation run
  GET  /api/v1/model-hub/{entry_id}/evaluations    → List evaluations
  POST /api/v1/model-hub/{entry_id}/promote        → Promote to active
  POST /api/v1/model-hub/{entry_id}/reject         → Reject candidate
  POST /api/v1/model-hub/{entry_id}/deprecate      → Deprecate active model
  GET  /api/v1/model-hub/{entry_id}/history        → Promotion event history
  POST /api/v1/model-hub/verify-signature          → Verify a peer node card signature
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import get_current_user
from app.federation.model_hub_service import ModelHubService, PromotionGate, GATE_MIN_ACCURACY, GATE_MIN_F1_MACRO, GATE_MIN_SUBGROUP_F1, GATE_MAX_PARITY_GAP, GATE_MAX_P95_LATENCY_MS, GATE_MAX_RAM_MB
from app.models.user import User

router = APIRouter(prefix="/model-hub", tags=["Model Hub"])


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class HubEntryCreate(BaseModel):
    model_card_id: str = Field(..., description="FK to existing model_cards.id")
    bucket: str = Field(default="krishinet-assets")
    object_key: str = Field(..., description="MinIO object key, e.g. models/<id>/weights.tflite")
    size_bytes: int = Field(..., gt=0)
    weights_sha256: str = Field(..., min_length=64, max_length=64)
    task_type: str = Field(..., description="disease_classifier | ndvi_estimator | advisory_adapter")
    crop_coverage: List[str] = Field(default_factory=list)
    card_json: Dict[str, Any] = Field(default_factory=dict)
    quantization: str = Field(default="int8")
    framework: str = Field(default="tflite")
    license_type: str = Field(default="Apache-2.0")


class EvaluationCreate(BaseModel):
    eval_dataset: str = Field(..., description="Name of the held-out eval dataset")
    accuracy: float = Field(..., ge=0.0, le=1.0)
    f1_macro: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    min_subgroup_f1: float = Field(..., ge=0.0, le=1.0)
    max_demographic_parity_gap: float = Field(..., ge=0.0, le=1.0)
    fairness_pass: bool
    inference_ms_p50: Optional[float] = None
    inference_ms_p95: Optional[float] = None
    peak_ram_mb: Optional[float] = None
    eval_commit_hash: Optional[str] = None


class PromotionAction(BaseModel):
    rationale: str = Field(..., min_length=10, description="Reason for promote/reject/deprecate")


class SignatureVerifyRequest(BaseModel):
    card_json: Dict[str, Any]
    signature_hex: str
    public_key_pem: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _entry_to_dict(entry) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "model_card_id": entry.model_card_id,
        "node_id": entry.node_id,
        "country_iso": entry.country_iso,
        "status": entry.status,
        "bucket": entry.bucket,
        "object_key": entry.object_key,
        "size_bytes": entry.size_bytes,
        "weights_sha256": entry.weights_sha256,
        "task_type": entry.task_type,
        "crop_coverage": entry.crop_coverage,
        "quantization": entry.quantization,
        "framework": entry.framework,
        "license_type": entry.license_type,
        "card_signed_by_node": entry.card_signed_by_node,
        "card_signature_hex": entry.card_signature_hex,
        "promoted_at": entry.promoted_at.isoformat() if entry.promoted_at else None,
        "deprecated_at": entry.deprecated_at.isoformat() if entry.deprecated_at else None,
        "created_at": entry.created_at.isoformat(),
    }


def _eval_to_dict(ev) -> Dict[str, Any]:
    return {
        "id": ev.id,
        "hub_entry_id": ev.hub_entry_id,
        "eval_dataset": ev.eval_dataset,
        "eval_node_id": ev.eval_node_id,
        "accuracy": ev.accuracy,
        "f1_macro": ev.f1_macro,
        "precision": ev.precision,
        "recall": ev.recall,
        "min_subgroup_f1": ev.min_subgroup_f1,
        "max_demographic_parity_gap": ev.max_demographic_parity_gap,
        "fairness_pass": ev.fairness_pass,
        "inference_ms_p50": ev.inference_ms_p50,
        "inference_ms_p95": ev.inference_ms_p95,
        "peak_ram_mb": ev.peak_ram_mb,
        "gate_passed": ev.gate_passed,
        "gate_detail": ev.gate_detail,
        "eval_commit_hash": ev.eval_commit_hash,
        "evaluated_at": ev.evaluated_at.isoformat(),
    }


def _event_to_dict(ev) -> Dict[str, Any]:
    return {
        "id": ev.id,
        "hub_entry_id": ev.hub_entry_id,
        "action": ev.action,
        "reviewer_node_id": ev.reviewer_node_id,
        "reviewer_country_iso": ev.reviewer_country_iso,
        "reviewer_role": ev.reviewer_role,
        "rationale": ev.rationale,
        "signature_hex": ev.signature_hex,
        "previous_status": ev.previous_status,
        "new_status": ev.new_status,
        "event_at": ev.event_at.isoformat(),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", summary="List Model Hub Catalog")
async def list_catalog(
    status: Optional[str] = Query(None, description="Filter by status: candidate|promoted|deprecated|rejected"),
    task_type: Optional[str] = Query(None),
    country_iso: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ModelHubService(db)
    entries = await svc.list_catalog(
        status=status, task_type=task_type, country_iso=country_iso,
        limit=limit, offset=offset
    )
    return {
        "total": len(entries),
        "limit": limit,
        "offset": offset,
        "entries": [_entry_to_dict(e) for e in entries],
        "promotion_gate_thresholds": {
            "min_accuracy": GATE_MIN_ACCURACY,
            "min_f1_macro": GATE_MIN_F1_MACRO,
            "min_subgroup_f1": GATE_MIN_SUBGROUP_F1,
            "max_demographic_parity_gap": GATE_MAX_PARITY_GAP,
            "max_p95_latency_ms": GATE_MAX_P95_LATENCY_MS,
            "max_ram_mb": GATE_MAX_RAM_MB,
        },
    }


@router.post("", summary="Register New Candidate Hub Entry", status_code=201)
async def register_entry(
    body: HubEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_researcher_or_admin(current_user)
    svc = ModelHubService(db)
    entry = await svc.register_entry(
        model_card_id=body.model_card_id,
        bucket=body.bucket,
        object_key=body.object_key,
        size_bytes=body.size_bytes,
        weights_sha256=body.weights_sha256,
        task_type=body.task_type,
        crop_coverage=body.crop_coverage,
        card_json=body.card_json,
        quantization=body.quantization,
        framework=body.framework,
        license_type=body.license_type,
    )
    return _entry_to_dict(entry)


@router.get("/{entry_id}", summary="Get Hub Entry Detail")
async def get_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ModelHubService(db)
    entry = await svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Hub entry '{entry_id}' not found.")
    return _entry_to_dict(entry)


@router.get("/{entry_id}/download-url", summary="Generate Presigned Download URL")
async def download_url(
    entry_id: str,
    expires_seconds: int = Query(3600, ge=300, le=86400),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ModelHubService(db)
    entry = await svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Hub entry '{entry_id}' not found.")

    # Only promoted models are downloadable by default
    if entry.status not in ("promoted",) and current_user.role not in (
        "researcher", "government_admin", "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Only promoted models are publicly downloadable. "
                   "Researchers/admins may download candidates.",
        )

    url = ModelHubService.generate_presigned_url(
        object_key=entry.object_key,
        expires_seconds=expires_seconds,
        bucket=entry.bucket,
    )
    return {
        "entry_id": entry_id,
        "object_key": entry.object_key,
        "weights_sha256": entry.weights_sha256,
        "size_bytes": entry.size_bytes,
        "download_url": url,
        "expires_seconds": expires_seconds,
        "verify_instruction": (
            f"sha256sum <downloaded-file>  # must equal {entry.weights_sha256}"
        ),
    }


@router.post("/{entry_id}/evaluations", summary="Submit Evaluation Run", status_code=201)
async def submit_evaluation(
    entry_id: str,
    body: EvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_researcher_or_admin(current_user)
    svc = ModelHubService(db)
    entry = await svc.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Hub entry '{entry_id}' not found.")

    ev = await svc.submit_evaluation(
        hub_entry_id=entry_id,
        eval_dataset=body.eval_dataset,
        accuracy=body.accuracy,
        f1_macro=body.f1_macro,
        precision=body.precision,
        recall=body.recall,
        min_subgroup_f1=body.min_subgroup_f1,
        max_demographic_parity_gap=body.max_demographic_parity_gap,
        fairness_pass=body.fairness_pass,
        inference_ms_p50=body.inference_ms_p50,
        inference_ms_p95=body.inference_ms_p95,
        peak_ram_mb=body.peak_ram_mb,
        eval_commit_hash=body.eval_commit_hash,
    )
    return _eval_to_dict(ev)


@router.get("/{entry_id}/evaluations", summary="List Evaluations for Hub Entry")
async def list_evaluations(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ModelHubService(db)
    evals = await svc.get_evaluations(entry_id)
    return {"hub_entry_id": entry_id, "evaluations": [_eval_to_dict(e) for e in evals]}


@router.post("/{entry_id}/promote", summary="Promote Candidate to Active")
async def promote_entry(
    entry_id: str,
    body: PromotionAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    svc = ModelHubService(db)
    try:
        entry = await svc.promote(
            hub_entry_id=entry_id,
            reviewer_role=current_user.role,
            rationale=body.rationale,
            reviewer_country_iso=current_user.country_iso,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"message": "Model promoted successfully.", "entry": _entry_to_dict(entry)}


@router.post("/{entry_id}/reject", summary="Reject Candidate Entry")
async def reject_entry(
    entry_id: str,
    body: PromotionAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    svc = ModelHubService(db)
    try:
        entry = await svc.reject(
            hub_entry_id=entry_id,
            reviewer_role=current_user.role,
            rationale=body.rationale,
            reviewer_country_iso=current_user.country_iso,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"message": "Model rejected.", "entry": _entry_to_dict(entry)}


@router.post("/{entry_id}/deprecate", summary="Deprecate Active Model")
async def deprecate_entry(
    entry_id: str,
    body: PromotionAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    svc = ModelHubService(db)
    try:
        entry = await svc.deprecate(
            hub_entry_id=entry_id,
            reviewer_role=current_user.role,
            rationale=body.rationale,
            reviewer_country_iso=current_user.country_iso,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"message": "Model deprecated.", "entry": _entry_to_dict(entry)}


@router.get("/{entry_id}/history", summary="Promotion Event History")
async def promotion_history(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ModelHubService(db)
    events = await svc.get_promotion_history(entry_id)
    return {
        "hub_entry_id": entry_id,
        "events": [_event_to_dict(e) for e in events],
    }


@router.post("/verify-signature", summary="Verify Peer Node Model Card Signature")
async def verify_signature(
    body: SignatureVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    valid = ModelHubService.verify_card_signature(
        card_dict=body.card_json,
        signature_hex=body.signature_hex,
        public_key_pem=body.public_key_pem,
    )
    return {
        "valid": valid,
        "message": "Signature is valid." if valid else "Signature verification FAILED.",
    }


# ── RBAC helpers ──────────────────────────────────────────────────────────────

def _require_researcher_or_admin(user: User) -> None:
    if user.role not in ("researcher", "government_admin", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Requires researcher or government_admin role.",
        )


def _require_admin(user: User) -> None:
    if user.role not in ("government_admin", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Requires government_admin role to manage Hub promotion lifecycle.",
        )
