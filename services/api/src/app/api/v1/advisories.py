"""
KrishiNet-BRICS - Sovereign AI Advisory API Endpoints.
Exposes generation, inspection, explainability, feedback, multilingual translation, and AI health probes.
"""

import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.explainability import explainability_service
from app.ai.gemini_client import gemini_client
from app.ai.orchestrator import advisory_orchestrator
from app.ai.rules.crop_config import CROP_AGRONOMIC_SPECS
from app.ai.translation import SUPPORTED_LANGUAGES, translation_service
from app.core.config import settings
from app.core.security import get_current_user_optional
from app.core.deps import get_db
from app.models.advisory import Advisory, AdvisoryAction, AdvisoryFeedback, KnowledgeDocument
from app.models.farm import Field as FieldModel
from app.schemas.advisory import AdvisoryContract

router = APIRouter(tags=["Advisories & Sovereign AI"])


# ----------------------------------------------------------------------------
# Request / Response Schemas
# ----------------------------------------------------------------------------

class GenerateAdvisoryRequest(BaseModel):
    language: str = Field(default="en", description="Target language (e.g. en, hi, mr, pt, ru, zh, ar, sw)")
    farmer_notes: Optional[str] = Field(None, max_length=1000, description="Optional farmer observations or queries")
    preferred_crop: Optional[str] = Field(None, description="Specific crop to generate advisory for")
    force_refresh: bool = Field(default=False, description="Bypass telemetry cache")


class AdvisoryFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="1 to 5 star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Farmer or extension officer feedback")
    practices_adopted: List[str] = Field(default_factory=list, description="List of practices implemented")


class TranslateAdvisoryRequest(BaseModel):
    target_language: str = Field(..., description="Target language code (e.g. hi, mr, pt, ru, zh, ar, sw)")


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------

@router.post("/fields/{field_id}/advisory", response_model=AdvisoryContract, status_code=status.HTTP_201_CREATED)
async def generate_field_advisory_endpoint(
    field_id: str,
    payload: GenerateAdvisoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Generates a sovereign, grounded, and explainable regenerative agronomic advisory for a field.
    Integrates satellite, soil, weather, RAG agronomy knowledge, and deterministic safety envelopes.
    """
    # Verify field exists
    stmt = select(FieldModel).where(FieldModel.id == field_id)
    res = await db.execute(stmt)
    field_row = res.scalar_one_or_none()
    if not field_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field with ID '{field_id}' not found.",
        )

    user_id = (
        getattr(current_user, "id", None)
        or (current_user.get("sub") if isinstance(current_user, dict) else None)
        if current_user
        else None
    )

    contract = await advisory_orchestrator.generate_advisory(
        field_id=field_id,
        db=db,
        user_id=user_id,
        language=payload.language,
        farmer_notes=payload.farmer_notes,
        preferred_crop=payload.preferred_crop,
        force_refresh=payload.force_refresh,
    )

    return contract


@router.get("/fields/{field_id}/advisories")
async def list_field_advisories_endpoint(
    field_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns chronological history of generated advisories for a field.
    """
    stmt = (
        select(Advisory)
        .where(Advisory.field_id == field_id)
        .order_by(desc(Advisory.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()

    return [
        {
            "advisory_id": a.id,
            "field_id": a.field_id,
            "generated_at": a.created_at.isoformat() if a.created_at else None,
            "confidence_score": a.confidence_score,
            "hallucination_guard_passed": a.hallucination_guard_passed,
            "language": a.language,
            "engine_mode": a.engine_mode,
            "top_crops": [c.get("crop") for c in a.top_3_crops if isinstance(c, dict)],
        }
        for a in rows
    ]


@router.get("/advisories/{advisory_id}", response_model=AdvisoryContract)
async def get_advisory_contract_endpoint(
    advisory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches full AdvisoryContract document by ID.
    """
    stmt = select(Advisory).where(Advisory.id == advisory_id)
    res = await db.execute(stmt)
    adv = res.scalar_one_or_none()
    if not adv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory '{advisory_id}' not found.",
        )

    if adv.full_advisory_json:
        return AdvisoryContract.model_validate(adv.full_advisory_json)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Advisory record corrupted: missing contract payload.",
    )


@router.get("/advisories/{advisory_id}/explainability")
async def get_advisory_explainability_endpoint(
    advisory_id: str,
    for_officer: bool = Query(default=False, description="If true, returns diagnostic telemetry view for extension officers"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns dual-presentation explainability view:
    - Default: Farmer plain-language visual trust brief
    - for_officer=true: In-depth biophysical diagnostic with directional signal weights and counterfactual statement
    """
    stmt = select(Advisory).where(Advisory.id == advisory_id)
    res = await db.execute(stmt)
    adv = res.scalar_one_or_none()
    if not adv or not adv.full_advisory_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory '{advisory_id}' not found.",
        )

    contract = AdvisoryContract.model_validate(adv.full_advisory_json)
    return explainability_service.format_explainability(contract, for_officer=for_officer)


@router.get("/advisories/{advisory_id}/trace")
async def get_advisory_execution_trace_endpoint(
    advisory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Inspects granular execution trace: pipeline timings, RAG documents retrieved,
    deterministic rules baseline, warnings, and confidence scoring components.
    """
    stmt = select(Advisory).where(Advisory.id == advisory_id)
    res = await db.execute(stmt)
    adv = res.scalar_one_or_none()
    if not adv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory '{advisory_id}' not found.",
        )

    return {
        "advisory_id": adv.id,
        "field_id": adv.field_id,
        "engine_mode": adv.engine_mode,
        "prompt_version": adv.prompt_version,
        "confidence_score": adv.confidence_score,
        "trace": adv.execution_trace or {},
    }


@router.get("/advisories/{advisory_id}/actions")
async def list_advisory_actions_endpoint(
    advisory_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the list of 30-day action calendar tasks for an advisory.
    """
    stmt = (
        select(AdvisoryAction)
        .where(AdvisoryAction.advisory_id == advisory_id)
        .order_by(AdvisoryAction.calendar_day)
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [
        {
            "action_id": a.id,
            "advisory_id": a.advisory_id,
            "calendar_day": a.calendar_day,
            "action_title": a.action_title,
            "action_description": a.action_description,
            "category": a.category,
            "is_completed": a.is_completed,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in rows
    ]


@router.post("/advisories/{advisory_id}/actions/{action_id}/complete")
async def complete_action_calendar_item_endpoint(
    advisory_id: str,
    action_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Toggles completion state of a 30-day action calendar task.
    Supports either UUID or day offset integer as action_id.
    """
    if action_id.isdigit():
        stmt = select(AdvisoryAction).where(
            AdvisoryAction.advisory_id == advisory_id,
            (AdvisoryAction.id == action_id) | (AdvisoryAction.calendar_day == int(action_id)),
        )
    else:
        stmt = select(AdvisoryAction).where(
            AdvisoryAction.id == action_id,
            AdvisoryAction.advisory_id == advisory_id,
        )
    res = await db.execute(stmt)
    action_row = res.scalar_one_or_none()
    if not action_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_id}' not found for advisory '{advisory_id}'.",
        )

    action_row.is_completed = not action_row.is_completed
    action_row.completed_at = datetime.datetime.now(datetime.timezone.utc) if action_row.is_completed else None
    await db.commit()

    return {
        "status": "success",
        "action_id": action_row.id,
        "is_completed": action_row.is_completed,
        "completed_at": action_row.completed_at.isoformat() if action_row.completed_at else None,
    }


@router.post("/advisories/{advisory_id}/feedback")
async def submit_advisory_feedback_endpoint(
    advisory_id: str,
    payload: AdvisoryFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Records farmer or extension officer adoption feedback and rating.
    """
    stmt = select(Advisory).where(Advisory.id == advisory_id)
    res = await db.execute(stmt)
    adv = res.scalar_one_or_none()
    if not adv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory '{advisory_id}' not found.",
        )

    user_id = (
        getattr(current_user, "id", None)
        or (current_user.get("sub") if isinstance(current_user, dict) else None)
        if current_user
        else "anonymous-farmer"
    )

    feedback_row = AdvisoryFeedback(
        advisory_id=advisory_id,
        user_id=user_id,
        rating=payload.rating,
        comment=payload.comment,
        practices_adopted=payload.practices_adopted,
    )
    db.add(feedback_row)
    await db.commit()

    return {
        "status": "recorded",
        "feedback_id": feedback_row.id,
        "advisory_id": advisory_id,
        "rating": feedback_row.rating,
    }


@router.post("/advisories/{advisory_id}/translate", response_model=AdvisoryContract)
async def translate_advisory_endpoint(
    advisory_id: str,
    payload: TranslateAdvisoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Dynamically translates an existing advisory into another supported BRICS language.
    Preserves all agronomic numbers, units, dates, citations, and structure invariants.
    """
    stmt = select(Advisory).where(Advisory.id == advisory_id)
    res = await db.execute(stmt)
    adv = res.scalar_one_or_none()
    if not adv or not adv.full_advisory_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisory '{advisory_id}' not found.",
        )

    contract = AdvisoryContract.model_validate(adv.full_advisory_json)
    translated = await translation_service.translate_advisory(
        contract=contract,
        target_language=payload.target_language,
    )

    return translated


@router.get("/ai/health")
async def ai_engine_health_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """
    Probes the health of the Sovereign AI Engine:
    - Gemini Model availability & circuit state
    - Daily token usage & quota headroom
    - RAG Knowledge Base indexing metrics
    - Supported crop agronomic catalogs & languages
    """
    # Count knowledge documents
    doc_count = (await db.execute(select(func.count(KnowledgeDocument.id)))).scalar() or 0

    return {
        "status": "healthy",
        "node_id": settings.NODE_ID,
        "node_country": settings.NODE_COUNTRY,
        "demo_mode": settings.DEMO_MODE,
        "gemini_model": settings.GEMINI_MODEL,
        "knowledge_base": {
            "indexed_documents": doc_count,
            "status": "ready",
        },
        "supported_crops": list(CROP_AGRONOMIC_SPECS.keys()),
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        "token_budget": {
            "daily_limit": settings.USER_DAILY_TOKEN_LIMIT,
            "circuit_breaker": "closed",
        },
    }
