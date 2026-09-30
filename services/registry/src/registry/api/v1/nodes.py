"""
BRICS Commons Registry - Node Management & Cryptographic Handshake Endpoints.
"""

import base64
import datetime
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from registry.core.config import settings
from registry.core.privacy_guard import validate_no_pii_or_fine_coordinates
from registry.core.security import (
    verify_ed25519_signature,
    verify_registry_admin,
    verify_replay_and_extract_payload,
)
from registry.db.session import get_db
from registry.models.node import RegistryAuditLog, RegistryNode, RegistryNodeKey
from registry.schemas.node import (
    KeyRotationRequest,
    KeyRotationResponse,
    NodeDetailResponse,
    NodeHeartbeatRequest,
    NodeHeartbeatResponse,
    NodeKeySummary,
    NodeRegistrationRequest,
    NodeRegistrationResponse,
    NodeStatusUpdateRequest,
)

router = APIRouter(prefix="/nodes", tags=["Sovereign Nodes Registry"])


@router.post(
    "/register",
    response_model=NodeRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a sovereign national agricultural node",
)
async def register_node(
    req: NodeRegistrationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Anti-leak privacy guard
    raw_body = await request.body()
    try:
        body_json = await request.json()
        validate_no_pii_or_fine_coordinates(body_json)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e

    # 2. Validate Ed25519 public key format (must be 32 bytes when base64 decoded)
    try:
        pub_bytes = base64.b64decode(req.public_key)
        if len(pub_bytes) != 32:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public key must be a valid 32-byte Base64-encoded Ed25519 key.",
        )

    # 3. Check for existing node
    stmt = select(RegistryNode).where(RegistryNode.id == req.node_id)
    result = await db.execute(stmt)
    existing_node = result.scalar_one_or_none()
    if existing_node:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node '{req.node_id}' is already registered with status '{existing_node.status}'.",
        )

    # 4. Status determination (auto-approve in development only)
    node_status = "approved" if settings.AUTO_APPROVE_DEV else "pending"
    approved_at = datetime.datetime.utcnow() if node_status == "approved" else None

    node = RegistryNode(
        id=req.node_id,
        country_code=req.country_code.upper(),
        organisation_name=req.organisation_name,
        status=node_status,
        api_base_url=req.api_base_url,
        capabilities=req.capabilities,
        version=req.version,
        contact_email=req.contact_email,
        approved_at=approved_at,
    )
    db.add(node)

    # Store initial Ed25519 public key
    key = RegistryNodeKey(
        node_id=req.node_id,
        public_key=req.public_key,
        key_version=1,
        status="active",
        valid_from=datetime.datetime.utcnow(),
    )
    db.add(key)

    # Immutable audit log
    audit = RegistryAuditLog(
        actor_id=req.node_id,
        action="node_registered",
        target_id=req.node_id,
        payload_hash=hashlib.sha256(raw_body).hexdigest(),
        details={"country": req.country_code, "status": node_status},
    )
    db.add(audit)
    await db.commit()

    return NodeRegistrationResponse(
        node_id=node.id,
        country_code=node.country_code,
        organisation_name=node.organisation_name,
        status=node.status,
        registered_at=node.registered_at,
        message=(
            "Node registration approved automatically in dev mode."
            if node_status == "approved"
            else "Node registration received. Pending administrator authorization."
        ),
    )


@router.get("", response_model=List[NodeDetailResponse], summary="List all registered sovereign nodes")
async def list_nodes(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RegistryNode)
    if status_filter:
        stmt = stmt.where(RegistryNode.status == status_filter)
    result = await db.execute(stmt)
    nodes = result.scalars().all()

    output = []
    now = datetime.datetime.utcnow()
    stale_delta = datetime.timedelta(minutes=settings.NODE_STALE_THRESHOLD_MINUTES)

    for n in nodes:
        # Check staleness
        is_stale = False
        if n.last_heartbeat_at and (now - n.last_heartbeat_at) > stale_delta:
            is_stale = True

        # Fetch active key
        key_stmt = (
            select(RegistryNodeKey)
            .where(RegistryNodeKey.node_id == n.id)
            .order_by(RegistryNodeKey.key_version.desc())
        )
        key_res = await db.execute(key_stmt)
        keys = key_res.scalars().all()

        active_key = None
        key_summaries = []
        for k in keys:
            if k.status in ["active", "grace_period"] and not active_key:
                active_key = k.public_key
            key_summaries.append(
                NodeKeySummary(
                    id=k.id,
                    public_key=k.public_key,
                    key_version=k.key_version,
                    status=k.status,
                    valid_from=k.valid_from,
                    expires_at=k.expires_at,
                )
            )

        output.append(
            NodeDetailResponse(
                id=n.id,
                country_code=n.country_code,
                organisation_name=n.organisation_name,
                status=n.status,
                api_base_url=n.api_base_url,
                capabilities=n.capabilities or [],
                version=n.version,
                contact_email=n.contact_email,
                registered_at=n.registered_at,
                approved_at=n.approved_at,
                last_heartbeat_at=n.last_heartbeat_at,
                is_stale=is_stale,
                active_key=active_key,
                keys=key_summaries,
                metrics_summary=n.metrics_summary or {},
            )
        )

    return output


@router.get("/{node_id}", response_model=NodeDetailResponse, summary="Get details for a registered node")
async def get_node(node_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    now = datetime.datetime.utcnow()
    is_stale = False
    if node.last_heartbeat_at and (now - node.last_heartbeat_at) > datetime.timedelta(
        minutes=settings.NODE_STALE_THRESHOLD_MINUTES
    ):
        is_stale = True

    key_stmt = (
        select(RegistryNodeKey)
        .where(RegistryNodeKey.node_id == node.id)
        .order_by(RegistryNodeKey.key_version.desc())
    )
    key_res = await db.execute(key_stmt)
    keys = key_res.scalars().all()

    active_key = None
    key_summaries = []
    for k in keys:
        if k.status in ["active", "grace_period"] and not active_key:
            active_key = k.public_key
        key_summaries.append(
            NodeKeySummary(
                id=k.id,
                public_key=k.public_key,
                key_version=k.key_version,
                status=k.status,
                valid_from=k.valid_from,
                expires_at=k.expires_at,
            )
        )

    return NodeDetailResponse(
        id=node.id,
        country_code=node.country_code,
        organisation_name=node.organisation_name,
        status=node.status,
        api_base_url=node.api_base_url,
        capabilities=node.capabilities or [],
        version=node.version,
        contact_email=node.contact_email,
        registered_at=node.registered_at,
        approved_at=node.approved_at,
        last_heartbeat_at=node.last_heartbeat_at,
        is_stale=is_stale,
        active_key=active_key,
        keys=key_summaries,
        metrics_summary=node.metrics_summary or {},
    )


@router.post("/{node_id}/approve", response_model=NodeDetailResponse, summary="Approve a pending node (Admin only)")
async def approve_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    _is_admin: bool = Depends(verify_registry_admin),
):
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    node.status = "approved"
    node.approved_at = datetime.datetime.utcnow()

    audit = RegistryAuditLog(
        actor_id="registry-admin",
        action="node_approved",
        target_id=node_id,
        payload_hash=hashlib.sha256(b"node_approved").hexdigest(),
        details={"status": "approved"},
    )
    db.add(audit)
    await db.commit()
    return await get_node(node_id, db)


@router.post("/{node_id}/suspend", response_model=NodeDetailResponse, summary="Suspend a node (Admin only)")
async def suspend_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    _is_admin: bool = Depends(verify_registry_admin),
):
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    node.status = "suspended"
    audit = RegistryAuditLog(
        actor_id="registry-admin",
        action="node_suspended",
        target_id=node_id,
        payload_hash=hashlib.sha256(b"node_suspended").hexdigest(),
        details={"status": "suspended"},
    )
    db.add(audit)
    await db.commit()
    return await get_node(node_id, db)


@router.post("/{node_id}/revoke", response_model=NodeDetailResponse, summary="Revoke a node (Admin only)")
async def revoke_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    _is_admin: bool = Depends(verify_registry_admin),
):
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    node.status = "revoked"

    # Revoke keys
    key_stmt = select(RegistryNodeKey).where(RegistryNodeKey.node_id == node_id)
    key_res = await db.execute(key_stmt)
    for k in key_res.scalars().all():
        k.status = "revoked"

    audit = RegistryAuditLog(
        actor_id="registry-admin",
        action="node_revoked",
        target_id=node_id,
        payload_hash=hashlib.sha256(b"node_revoked").hexdigest(),
        details={"status": "revoked"},
    )
    db.add(audit)
    await db.commit()
    return await get_node(node_id, db)


@router.post(
    "/{node_id}/heartbeat",
    response_model=NodeHeartbeatResponse,
    summary="Record node heartbeat with non-PII aggregate counts",
)
async def node_heartbeat(
    node_id: str,
    req: NodeHeartbeatRequest,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature-Ed25519"),
    x_timestamp: Optional[str] = Header(None, alias="X-Signature-Timestamp"),
    x_nonce: Optional[str] = Header(None, alias="X-Signature-Nonce"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Anti-leak privacy guard
    raw_body = await request.body()
    try:
        body_json = await request.json()
        validate_no_pii_or_fine_coordinates(body_json)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e

    # 2. Lookup Node
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    # Node must be approved
    if node.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Node '{node_id}' cannot send heartbeats in status '{node.status}'.",
        )

    # 3. Retrieve valid keys for node
    key_stmt = (
        select(RegistryNodeKey)
        .where(
            RegistryNodeKey.node_id == node_id,
            RegistryNodeKey.status.in_(["active", "grace_period"]),
        )
        .order_by(RegistryNodeKey.key_version.desc())
    )
    key_res = await db.execute(key_stmt)
    valid_keys = key_res.scalars().all()
    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No active signing keys found for node '{node_id}'.",
        )

    # 4. In production or when headers are present, verify signature & replay
    if x_signature and x_timestamp and x_nonce:
        verified = False
        last_err = None
        for k in valid_keys:
            try:
                verify_replay_and_extract_payload(
                    node_id=node_id,
                    timestamp_str=x_timestamp,
                    nonce=x_nonce,
                    signature_b64=x_signature,
                    body_bytes=raw_body,
                    public_key_b64=k.public_key,
                )
                verified = True
                break
            except HTTPException as auth_err:
                last_err = auth_err
        if not verified and last_err:
            raise last_err
    elif settings.ENVIRONMENT in ["prod", "production"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signed headers (X-Signature-Ed25519, X-Signature-Timestamp, X-Signature-Nonce) are mandatory in production.",
        )

    # 5. Update heartbeat & aggregates
    now = datetime.datetime.utcnow()
    node.last_heartbeat_at = now
    node.is_stale = False
    node.version = req.api_version
    node.metrics_summary = req.aggregate_counts.model_dump()

    await db.commit()

    return NodeHeartbeatResponse(
        node_id=node.id,
        status=req.status,
        last_heartbeat_at=now,
        is_stale=False,
        acknowledged=True,
    )


@router.post(
    "/{node_id}/rotate-key",
    response_model=KeyRotationResponse,
    summary="Rotate Ed25519 node public key with overlap grace period",
)
async def rotate_key(
    node_id: str,
    req: KeyRotationRequest,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature-Ed25519"),
    x_timestamp: Optional[str] = Header(None, alias="X-Signature-Timestamp"),
    x_nonce: Optional[str] = Header(None, alias="X-Signature-Nonce"),
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()

    # 1. Lookup Node
    stmt = select(RegistryNode).where(RegistryNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found.")

    if node.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Key rotation denied: Node '{node_id}' is not in approved state.",
        )

    # 2. Get active keys to verify signature
    key_stmt = (
        select(RegistryNodeKey)
        .where(RegistryNodeKey.node_id == node_id, RegistryNodeKey.status == "active")
        .order_by(RegistryNodeKey.key_version.desc())
    )
    key_res = await db.execute(key_stmt)
    active_keys = key_res.scalars().all()
    if not active_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active key available to authorize rotation.",
        )

    # 3. Verify signature
    if x_signature and x_timestamp and x_nonce:
        verified = False
        last_err = None
        for k in active_keys:
            try:
                verify_replay_and_extract_payload(
                    node_id=node_id,
                    timestamp_str=x_timestamp,
                    nonce=x_nonce,
                    signature_b64=x_signature,
                    body_bytes=raw_body,
                    public_key_b64=k.public_key,
                )
                verified = True
                break
            except HTTPException as err:
                last_err = err
        if not verified and last_err:
            raise last_err
    elif settings.ENVIRONMENT in ["prod", "production"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Rotation must be signed by the existing active private key.",
        )

    # 4. Transition current active keys to grace_period
    now = datetime.datetime.utcnow()
    grace_expires = now + datetime.timedelta(hours=settings.KEY_ROTATION_GRACE_HOURS)
    for k in active_keys:
        k.status = "grace_period"
        k.expires_at = grace_expires

    # 5. Insert new key as active
    new_key = RegistryNodeKey(
        node_id=node_id,
        public_key=req.new_public_key,
        key_version=req.key_version,
        status="active",
        valid_from=now,
    )
    db.add(new_key)

    audit = RegistryAuditLog(
        actor_id=node_id,
        action="key_rotated",
        target_id=node_id,
        payload_hash=hashlib.sha256(raw_body).hexdigest(),
        details={"new_key_version": req.key_version, "grace_hours": settings.KEY_ROTATION_GRACE_HOURS},
    )
    db.add(audit)
    await db.commit()

    return KeyRotationResponse(
        node_id=node_id,
        key_version=req.key_version,
        grace_period_expires_at=grace_expires,
        message=f"Key version {req.key_version} activated. Previous key remains valid for {settings.KEY_ROTATION_GRACE_HOURS} hours.",
    )
