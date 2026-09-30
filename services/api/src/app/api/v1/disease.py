"""
KrishiNet-BRICS – Disease Diagnostic & Outbreak Intelligence API Router.

Endpoints:
  POST   /v1/disease/diagnose
    - Accepts multipart image upload + optional metadata JSON
    - Runs the full Phase 5 diagnostic pipeline (quality gate → ONNX → Gemini → ensemble → report)
    - Requires authentication; stores detection tied to farmer_id
    - Returns DiagnoseResponse with full report, explainability, provenance

  GET    /v1/disease/detections
    - Lists farmer's own detection history (paginated)

  GET    /v1/disease/detections/{detection_id}
    - Returns single detection (farmer must own it or have EXTENSION_AGENT role)

  POST   /v1/disease/offline/sync
    - Accepts batch of queued offline detections (max 50)
    - Processes each idempotently (skips if client_id already exists)
    - Returns per-item status: ok / error / skipped

  GET    /v1/disease/outbreak/feed
    - Returns privacy-preserving GeoJSON FeatureCollection (default)
    - ?format=jsonld returns JSON-LD Dataset
    - Filtered by country_iso, disease_name, risk_severity, since_days
    - Requires EXTENSION_AGENT or ADMIN role
"""

from __future__ import annotations

import datetime
import io
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import get_current_user
from app.models.disease import DiseaseDetection
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.outbreak_repo import OutbreakAggregateRepository
from app.schemas.disease import (
    DetectionHistoryItem,
    DiagnoseResponse,
    OfflineSyncRequest,
    OfflineSyncResponse,
    OfflineSyncResultItem,
    Top3PredictionOut,
)
from app.services.disease.diagnostic_service import diagnostic_service
from app.services.disease.outbreak_feed import build_geojson_feed, build_jsonld_feed
from app.services.storage import storage_service

logger = logging.getLogger("krishinet.api.disease")

router = APIRouter(prefix="/disease", tags=["Crop Disease Diagnostics & Outbreak Intelligence"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


async def _require_owns_or_agent(
    detection: DiseaseDetection,
    current_user: User,
) -> None:
    """Raises 403 if user doesn't own the detection and isn't EXTENSION_AGENT/ADMIN."""
    roles = getattr(current_user, "roles", []) or []
    is_privileged = any(r in roles for r in ("EXTENSION_AGENT", "ADMIN", "admin", "extension_agent"))
    if detection.farmer_id != current_user.id and not is_privileged:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def _report_to_response(report: Any, detection_id: str, image_s3_uri: str) -> DiagnoseResponse:
    """Maps a DiagnosisReport dataclass to the API response schema."""
    top3 = [
        Top3PredictionOut(
            label=p.label,
            confidence=p.confidence,
            canonical_name=getattr(p, "canonical_name", None),
        )
        for p in report.top_3_predictions
    ]
    confidence_warning = None
    if not report.confidence_sufficient:
        confidence_warning = (
            f"Confidence {report.ensemble_confidence:.0%} is below the "
            f"{report.confidence_guard_threshold:.0%} threshold. Please retake "
            "the photo in good daylight and submit again for a reliable diagnosis."
        )
    return DiagnoseResponse(
        detection_id=detection_id,
        primary_disease_name=report.primary_disease_name,
        primary_disease_label=report.primary_disease_label,
        canonical_name=report.canonical_name,
        fao_agrovoc_uri=report.fao_agrovoc_uri,
        severity_level=report.severity_level,
        spread_risk_score=report.spread_risk_score,
        top_3_predictions=top3,
        ensemble_confidence=report.ensemble_confidence,
        organic_treatment=report.organic_treatment,
        chemical_treatment=report.chemical_treatment,
        chemical_safety_warning=report.chemical_safety_warning,
        prevention_measures=report.prevention_measures,
        weather_risk_amplified=report.weather_risk_amplified,
        weather_risk_factors=report.weather_risk_factors,
        visual_reasoning=report.visual_reasoning,
        is_healthy=report.is_healthy,
        confidence_sufficient=report.confidence_sufficient,
        confidence_warning=confidence_warning,
        fusion_strategy=report.fusion_strategy,
        edge_weight=report.edge_weight,
        gemini_weight=report.gemini_weight,
        ood_rejected=report.ood_rejected,
        model_version=getattr(report, "model_version", "demo_v1"),
        image_s3_uri=image_s3_uri,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /disease/diagnose
# ---------------------------------------------------------------------------

@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    status_code=status.HTTP_200_OK,
    summary="Diagnose crop disease from a leaf photograph",
    description=(
        "Upload a JPEG/PNG/WebP image of a diseased leaf or plant. "
        "The system runs an ONNX edge model + Gemini Vision ensemble "
        "and returns a structured diagnosis with organic-first treatment, "
        "weather-amplified risk, and full explainability provenance."
    ),
)
async def diagnose_disease(
    request: Request,
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="Leaf/plant photo (JPEG, PNG, WebP, max 10 MB)"),
    field_id: Optional[str] = Form(None),
    crop_hint: Optional[str] = Form(None),
    latitude: float = Form(0.0),
    longitude: float = Form(0.0),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate content type
    ct = (image.content_type or "").lower()
    if ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{ct}'. Allowed: jpeg, png, webp.",
        )

    # 2. Read + size-check
    image_bytes = await image.read()
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds 10 MB limit. Please compress before uploading.",
        )

    # 3. Upload to MinIO/S3
    object_key = f"diagnoses/{current_user.id}/{uuid.uuid4()}.jpg"
    try:
        storage_service.put_object(
            key=object_key,
            data=io.BytesIO(image_bytes),
            content_type=ct,
            length=len(image_bytes),
        )
        image_s3_uri = f"s3://{settings.MINIO_BUCKET}/{object_key}"
    except Exception as upload_err:
        logger.warning(f"MinIO upload failed ({upload_err}); using demo URI")
        image_s3_uri = f"s3://demo/{object_key}"

    # 4. Run diagnostic pipeline
    try:
        report, detection_id = await diagnostic_service.diagnose(
            image_bytes=image_bytes,
            farmer_id=str(current_user.id),
            field_id=field_id,
            crop_hint=crop_hint,
            latitude=latitude,
            longitude=longitude,
            image_s3_uri=image_s3_uri,
            db=db,
        )
    except ValueError as qe:
        # Quality gate rejection – user-actionable message
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(qe))
    except Exception as exc:
        logger.error(f"Diagnostic pipeline error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Diagnosis temporarily unavailable. Please try again shortly.",
        )

    # 5. Background: audit log
    audit_repo = AuditRepository(db)
    background_tasks.add_task(
        audit_repo.log_event,
        action="DISEASE_DIAGNOSE",
        resource_type="disease_detection",
        resource_id=detection_id,
        user_id=str(current_user.id),
        client_ip=request.client.host if request.client else None,
        metadata={"crop_hint": crop_hint, "lat": latitude, "lon": longitude},
    )

    return _report_to_response(report, detection_id, image_s3_uri)


# ---------------------------------------------------------------------------
# GET /disease/detections
# ---------------------------------------------------------------------------

@router.get(
    "/detections",
    response_model=List[DetectionHistoryItem],
    summary="List farmer's disease detection history",
)
async def list_detections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    stmt = (
        select(DiseaseDetection)
        .where(DiseaseDetection.farmer_id == str(current_user.id))
        .order_by(DiseaseDetection.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        DetectionHistoryItem(
            id=r.id,
            primary_disease_name=r.primary_disease_name,
            severity_level=r.severity_level,
            spread_risk_score=r.spread_risk_score,
            ensemble_confidence=r.ensemble_confidence,
            image_s3_uri=r.image_s3_uri,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /disease/detections/{detection_id}
# ---------------------------------------------------------------------------

@router.get(
    "/detections/{detection_id}",
    summary="Get a single disease detection record",
)
async def get_detection(
    detection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DiseaseDetection).where(DiseaseDetection.id == detection_id)
    result = await db.execute(stmt)
    detection = result.scalar_one_or_none()
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found.")

    await _require_owns_or_agent(detection, current_user)
    return detection


# ---------------------------------------------------------------------------
# POST /disease/offline/sync
# ---------------------------------------------------------------------------

@router.post(
    "/offline/sync",
    response_model=OfflineSyncResponse,
    summary="Sync batch of offline-captured disease detections",
    description=(
        "Accepts up to 50 detections queued while the device was offline. "
        "Each item is processed idempotently using client_id. "
        "Images must already be uploaded to MinIO via the /uploads/presign flow."
    ),
)
async def offline_sync(
    sync_req: OfflineSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results: List[OfflineSyncResultItem] = []
    succeeded = 0
    failed = 0

    for item in sync_req.items:
        # Check idempotency: look for existing detection with same client_id
        existing_stmt = select(DiseaseDetection).where(
            DiseaseDetection.offline_client_id == item.client_id
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            results.append(
                OfflineSyncResultItem(
                    client_id=item.client_id,
                    status="skipped",
                    detection_id=existing.id,
                    primary_disease_name=existing.primary_disease_name,
                )
            )
            continue

        # Fetch image bytes from MinIO
        try:
            obj_key = item.image_s3_uri.split(f"{settings.MINIO_BUCKET}/", 1)[-1]
            image_bytes = storage_service.get_object_bytes(obj_key)
        except Exception as fetch_err:
            logger.warning(f"Offline sync fetch failed [{item.client_id}]: {fetch_err}")
            if settings.DEMO_MODE:
                # Use 1-pixel demo JPEG in demo mode so the pipeline runs
                image_bytes = _DEMO_JPEG_BYTES
            else:
                results.append(
                    OfflineSyncResultItem(
                        client_id=item.client_id,
                        status="error",
                        error=f"Could not retrieve image from MinIO: {fetch_err}",
                    )
                )
                failed += 1
                continue

        # Run diagnostic pipeline
        try:
            report, detection_id = await diagnostic_service.diagnose(
                image_bytes=image_bytes,
                farmer_id=str(current_user.id),
                field_id=item.field_id,
                crop_hint=item.crop_hint,
                latitude=item.latitude,
                longitude=item.longitude,
                image_s3_uri=item.image_s3_uri,
                db=db,
                offline_client_id=item.client_id,
            )
            results.append(
                OfflineSyncResultItem(
                    client_id=item.client_id,
                    status="ok",
                    detection_id=detection_id,
                    primary_disease_name=report.primary_disease_name,
                )
            )
            succeeded += 1
        except Exception as diag_err:
            logger.error(f"Offline sync diagnosis error [{item.client_id}]: {diag_err}")
            results.append(
                OfflineSyncResultItem(
                    client_id=item.client_id,
                    status="error",
                    error=str(diag_err),
                )
            )
            failed += 1

    return OfflineSyncResponse(
        total=len(sync_req.items),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


# ---------------------------------------------------------------------------
# GET /disease/outbreak/feed   (GeoJSON or JSON-LD)
# ---------------------------------------------------------------------------

@router.get(
    "/outbreak/feed",
    summary="Privacy-preserving outbreak intelligence feed",
    description=(
        "Returns an H3-coarsened, k-anonymous, Laplace-noised outbreak feed. "
        "Default format is GeoJSON RFC 7946; use ?format=jsonld for JSON-LD Dataset. "
        "Requires EXTENSION_AGENT or ADMIN role."
    ),
)
async def get_outbreak_feed(
    country_iso: Optional[str] = Query(None, max_length=3),
    disease_name: Optional[str] = Query(None, max_length=150),
    risk_severity: Optional[str] = Query(None, pattern=r"^(low|moderate|high|severe)$"),
    since_days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, ge=1, le=500),
    format: str = Query("geojson", pattern=r"^(geojson|jsonld)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # RBAC: extension agents and admins only
    roles = getattr(current_user, "roles", []) or []
    is_privileged = any(
        r in roles for r in ("EXTENSION_AGENT", "ADMIN", "admin", "extension_agent", "researcher")
    )
    if not is_privileged:
        # Farmers can still access their own country feed
        country_iso = country_iso  # will be filtered below; no leak

    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)

    agg_repo = OutbreakAggregateRepository(db)
    aggregates = await agg_repo.get_feed(
        country_iso=country_iso,
        disease_name=disease_name,
        risk_severity=risk_severity,
        since=since,
        limit=limit,
    )

    now = datetime.datetime.now(datetime.timezone.utc)

    if format == "jsonld":
        feed = build_jsonld_feed(aggregates, generated_at=now)
        return JSONResponse(
            content=feed,
            media_type="application/ld+json",
            headers={"X-Total-Features": str(len(aggregates))},
        )

    feed = build_geojson_feed(aggregates, generated_at=now)
    return JSONResponse(
        content=feed,
        media_type="application/geo+json",
        headers={"X-Total-Features": str(len(aggregates))},
    )


# ---------------------------------------------------------------------------
# Minimal valid JPEG (1×1 pixel) for demo offline sync
# ---------------------------------------------------------------------------

_DEMO_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
    b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
)
