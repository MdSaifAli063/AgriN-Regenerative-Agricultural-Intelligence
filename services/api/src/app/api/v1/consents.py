import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.core.security import get_current_user
from app.federation.consent_manager import ConsentManager, ConsentScopeUpdate, _global_ledger
from app.models.user import Consent, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.consent_repo import ConsentRepository
from app.schemas.consent import ConsentResponse, ConsentUpdateRequest

router = APIRouter(prefix="/consents", tags=["Farmer Consent & Data Sovereignty"])


class RevokeConsentRequest(BaseModel):
    scopes: List[str] = Field(..., min_length=1, description="Scopes to revoke: soil, disease/telemetry, federated")
    reason: str = Field("Farmer requested data withdrawal", min_length=3)


@router.get("", response_model=ConsentResponse)
async def get_my_consent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve active data-sharing consent preferences for the authenticated farmer."""
    repo = ConsentRepository(db)
    consent = await repo.get_by_user(current_user.id)
    if not consent:
        # Default consent
        consent = Consent(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            share_anonymized_soil=True,
            share_outbreak_telemetry=True,
            participate_in_federated_learning=True,
        )
        await repo.create(consent)
    return consent


@router.post("", response_model=ConsentResponse)
async def update_consent(
    consent_in: ConsentUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update granular consent flags, generate Kantara-compliant consent receipt,
    and append an immutable block to the tamper-evident ledger.
    """
    manager = ConsentManager()
    consent, receipt, block = await manager.update_user_consent(
        user_id=current_user.id,
        updates=ConsentScopeUpdate(
            share_anonymized_soil=consent_in.share_anonymized_soil,
            share_outbreak_telemetry=consent_in.share_outbreak_telemetry,
            participate_in_federated_learning=consent_in.participate_in_federated_learning,
            reason="Farmer updated preferences",
        ),
        db=db,
    )

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="UPDATE_CONSENT",
        resource_type="consent",
        resource_id=consent.id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={
            "scopes": consent_in.model_dump(),
            "receipt_id": receipt.receipt_id,
            "block_index": block.block_index,
            "block_hash": block.block_hash,
        },
    )

    return consent


@router.post("/revoke")
async def revoke_consent_with_propagation(
    req: RevokeConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explicitly revoke consent scopes with immediate revocation propagation
    (purging farmer from active federated learning cohorts and egress queues).
    """
    manager = ConsentManager()
    consent, receipt, block = await manager.revoke_consent(
        user_id=current_user.id,
        scopes_to_revoke=req.scopes,
        reason=req.reason,
        db=db,
    )

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="REVOKE_CONSENT",
        resource_type="consent",
        resource_id=consent.id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={
            "revoked_scopes": req.scopes,
            "reason": req.reason,
            "receipt_id": receipt.receipt_id,
            "block_index": block.block_index,
        },
    )

    return {
        "status": "revoked",
        "revocation_propagated": True,
        "receipt": receipt.model_dump(),
        "ledger_block": block.model_dump(),
        "current_consent": {
            "share_anonymized_soil": consent.share_anonymized_soil,
            "share_outbreak_telemetry": consent.share_outbreak_telemetry,
            "participate_in_federated_learning": consent.participate_in_federated_learning,
        },
    }


@router.get("/receipt")
async def get_latest_receipt(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve or generate the latest signed Kantara consent receipt for the user."""
    repo = ConsentRepository(db)
    consent = await repo.get_by_user(current_user.id)
    scopes = {
        "share_anonymized_soil": consent.share_anonymized_soil if consent else True,
        "share_outbreak_telemetry": consent.share_outbreak_telemetry if consent else True,
        "participate_in_federated_learning": consent.participate_in_federated_learning if consent else True,
    }
    manager = ConsentManager()
    receipt = manager.generate_receipt(current_user.id, scopes)
    return receipt.model_dump()


@router.get("/ledger")
async def get_consent_ledger(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Retrieve blocks from the tamper-evident cryptographic consent audit ledger."""
    chain = _global_ledger.chain[-limit:]
    return [b.model_dump() for b in reversed(chain)]


@router.get("/verify-ledger")
async def verify_ledger_chain(
    current_user: User = Depends(get_current_user),
):
    """Verify cryptographic integrity (SHA-256 hash chaining) of the consent ledger."""
    is_valid, error = _global_ledger.verify_chain()
    return {
        "is_valid": is_valid,
        "total_blocks": len(_global_ledger.chain),
        "integrity_status": "VERIFIED_TAMPER_EVIDENT" if is_valid else "CORRUPTED",
        "error": error,
    }


@router.delete("/{scope}", response_model=ConsentResponse)
async def revoke_consent_scope(
    scope: str = Path(..., description="Scope to revoke: soil, disease, federated"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly revoke a specific consent scope."""
    manager = ConsentManager()
    consent, receipt, block = await manager.revoke_consent(
        user_id=current_user.id,
        scopes_to_revoke=[scope],
        reason=f"Revocation of {scope}",
        db=db,
    )

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="REVOKE_CONSENT_SCOPE",
        resource_type="consent",
        resource_id=consent.id,
        user_id=current_user.id,
        client_ip=request.client.host if request and request.client else None,
        details={"revoked_scope": scope, "receipt_id": receipt.receipt_id},
    )

    return consent


@router.post("/delete-my-data")
async def delete_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the comprehensive 'Right to be Forgotten' procedure:
    Permanently erases farmer profile, fields, advisories, detections, MinIO media, and messaging logs.
    """
    from app.services.privacy.retention import DataRetentionManager

    result = await DataRetentionManager.delete_farmer_data(db=db, user_id=current_user.id)
    return result

