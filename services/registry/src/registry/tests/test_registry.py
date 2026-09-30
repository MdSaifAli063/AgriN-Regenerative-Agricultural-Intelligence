"""
BRICS Commons Registry - Test Suite (Part 7A).
Validates anti-leak privacy guard, Ed25519 authentication, replay protection,
node lifecycle, key rotation, and discovery document.
"""

import base64
import json
import time
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from registry.core.privacy_guard import validate_no_pii_or_fine_coordinates, PrivacyViolationError


def _make_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(pub_bytes).decode("utf-8")
    return priv, pub_b64


def _create_signed_headers(priv: ed25519.Ed25519PrivateKey, node_id: str, body_bytes: bytes, ts_offset: float = 0):
    import hashlib
    ts = str(time.time() + ts_offset)
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    msg = f"{node_id}:{ts}:{nonce}:{body_hash}".encode("utf-8")
    sig = base64.b64encode(priv.sign(msg)).decode("utf-8")
    return {
        "X-Node-ID": node_id,
        "X-Signature-Timestamp": ts,
        "X-Signature-Nonce": nonce,
        "X-Signature-Ed25519": sig,
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_health_and_discovery(client):
    """Verifies health check and well-known federation discovery document."""
    # Health check
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["privacy_guard_active"] is True
    assert data["max_coordinate_decimals"] == 2

    # Discovery Document
    disc_res = await client.get("/.well-known/agrin-registry.json")
    assert disc_res.status_code == 200
    disc = disc_res.json()
    assert disc["agrin_version"] == "1.0.0"
    assert disc["signature_algorithm"] == "Ed25519"
    assert "stac-1.0.0" in disc["supported_protocols"]
    assert "flower-fl-grpc" in disc["supported_protocols"]
    assert "IND" in disc["participating_nations"]


@pytest.mark.asyncio
async def test_privacy_guard_rejects_pii():
    """Privacy guard must strictly raise PrivacyViolationError if farmer PII is present."""
    # 1. Direct PII key
    with pytest.raises(PrivacyViolationError):
        validate_no_pii_or_fine_coordinates({"node_id": "test", "farmer_name": "Ramesh"})

    # 2. Nested phone number
    with pytest.raises(PrivacyViolationError):
        validate_no_pii_or_fine_coordinates({"metadata": {"phone_number": "+919876543210"}})

    # 3. Cadastral boundary / polygon
    with pytest.raises(PrivacyViolationError):
        validate_no_pii_or_fine_coordinates({"farm_boundary": [[[78.5, 20.7], [78.6, 20.7]]]})


@pytest.mark.asyncio
async def test_privacy_guard_coordinate_precision():
    """Privacy guard must reject coordinates with > 2 decimal places and allow coarse coordinates."""
    # 4 decimals precision (farm-level ~10m) -> REJECT
    with pytest.raises(PrivacyViolationError):
        validate_no_pii_or_fine_coordinates({"latitude": 20.7453, "longitude": 78.5982})

    # Array coordinate with 3 decimals -> REJECT
    with pytest.raises(PrivacyViolationError):
        validate_no_pii_or_fine_coordinates({"coordinates": [78.591, 20.74]})

    # Coarse 2 decimals (district centroid ~1.1km) -> ACCEPT (no exception)
    validate_no_pii_or_fine_coordinates({"latitude": 20.74, "longitude": 78.60})


@pytest.mark.asyncio
async def test_node_registration_and_extra_field_rejection(client):
    """Tests node registration handshake and extra='forbid' constraint."""
    priv, pub_b64 = _make_keypair()

    # Extra arbitrary field -> Must be rejected with 422 Unprocessable Entity
    bad_payload = {
        "node_id": "node-ind-test-01",
        "country_code": "IND",
        "organisation_name": "ICAR India",
        "public_key": pub_b64,
        "capabilities": ["stac"],
        "api_base_url": "http://api.krishinet.in",
        "version": "1.0.0",
        "contact_email": "admin@icar.gov.in",
        "unauthorized_extra_field": "leak_attempt",
    }
    bad_res = await client.post("/registry/v1/nodes/register", json=bad_payload)
    assert bad_res.status_code == 422

    # Valid Registration
    valid_payload = {
        "node_id": "node-ind-test-01",
        "country_code": "IND",
        "organisation_name": "ICAR India",
        "public_key": pub_b64,
        "capabilities": ["stac", "flower_fl"],
        "api_base_url": "http://api.krishinet.in",
        "version": "1.0.0",
        "contact_email": "admin@icar.gov.in",
    }
    res = await client.post("/registry/v1/nodes/register", json=valid_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["node_id"] == "node-ind-test-01"
    assert data["country_code"] == "IND"

    # Duplicate registration -> 409 Conflict
    dup_res = await client.post("/registry/v1/nodes/register", json=valid_payload)
    assert dup_res.status_code == 409


@pytest.mark.asyncio
async def test_node_approval_lifecycle(client):
    """Verifies node approval, suspension, and revocation lifecycle."""
    _, pub_b64 = _make_keypair()
    node_id = "node-bra-embrapa-01"

    await client.post(
        "/registry/v1/nodes/register",
        json={
            "node_id": node_id,
            "country_code": "BRA",
            "organisation_name": "Embrapa Brazil",
            "public_key": pub_b64,
            "capabilities": ["stac", "disease_inference"],
            "api_base_url": "http://embrapa.gov.br/agrin",
            "version": "1.0.0",
            "contact_email": "contato@embrapa.br",
        },
    )

    # Suspend node
    susp_res = await client.post(f"/registry/v1/nodes/{node_id}/suspend")
    assert susp_res.status_code == 200
    assert susp_res.json()["status"] == "suspended"

    # Approve node
    appr_res = await client.post(f"/registry/v1/nodes/{node_id}/approve")
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "approved"

    # Revoke node
    rev_res = await client.post(f"/registry/v1/nodes/{node_id}/revoke")
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_ed25519_signed_heartbeat_and_replay_protection(client):
    """Verifies Ed25519 signature verification and anti-replay protection."""
    priv, pub_b64 = _make_keypair()
    node_id = "node-zaf-arc-01"

    # 1. Register approved node
    await client.post(
        "/registry/v1/nodes/register",
        json={
            "node_id": node_id,
            "country_code": "ZAF",
            "organisation_name": "ARC South Africa",
            "public_key": pub_b64,
            "capabilities": ["stac", "flower_fl"],
            "api_base_url": "http://arc.agric.za",
            "version": "1.0.0",
            "contact_email": "admin@arc.agric.za",
        },
    )

    hb_payload = {
        "status": "healthy",
        "api_version": "1.0.0",
        "active_models": ["MobileNetV3-BRICS-Disease-Int8"],
        "aggregate_counts": {
            "farmers_active": 350,
            "hectares_regenerated": 980,
            "water_saved_ml": 42,
            "co2e_sequestered_tonnes": 110,
            "validated_detections": 180,
            "outbreaks_reported": 4,
        },
    }
    body_bytes = json.dumps(hb_payload, sort_keys=True).encode("utf-8")

    # 2. Valid signed request
    headers = _create_signed_headers(priv, node_id, body_bytes)
    res = await client.post(f"/registry/v1/nodes/{node_id}/heartbeat", content=body_bytes, headers=headers)
    assert res.status_code == 200
    assert res.json()["acknowledged"] is True

    # 3. Replay attack: Sending exact same headers & body -> Must be rejected with 401
    replay_res = await client.post(f"/registry/v1/nodes/{node_id}/heartbeat", content=body_bytes, headers=headers)
    assert replay_res.status_code == 401
    assert "Replay attack detected" in replay_res.json()["detail"]

    # 4. Expired timestamp drift (> 300 seconds ago) -> Must be rejected with 401
    expired_headers = _create_signed_headers(priv, node_id, body_bytes, ts_offset=-350)
    exp_res = await client.post(f"/registry/v1/nodes/{node_id}/heartbeat", content=body_bytes, headers=expired_headers)
    assert exp_res.status_code == 401
    assert "drift exceeds" in exp_res.json()["detail"]

    # 5. Tampered payload -> Signature mismatch rejected with 401
    tampered_bytes = json.dumps({**hb_payload, "status": "degraded"}, sort_keys=True).encode("utf-8")
    tampered_headers = _create_signed_headers(priv, node_id, body_bytes)  # signature for original body_bytes
    tamp_res = await client.post(f"/registry/v1/nodes/{node_id}/heartbeat", content=tampered_bytes, headers=tampered_headers)
    assert tamp_res.status_code == 401


@pytest.mark.asyncio
async def test_key_rotation_with_grace_period(client):
    """Verifies node key rotation with overlap grace period window."""
    priv1, pub_b64_1 = _make_keypair()
    _, pub_b64_2 = _make_keypair()
    node_id = "node-rotation-test"

    # Register with key 1
    await client.post(
        "/registry/v1/nodes/register",
        json={
            "node_id": node_id,
            "country_code": "IND",
            "organisation_name": "Rotation Org",
            "public_key": pub_b64_1,
            "capabilities": ["stac"],
            "api_base_url": "http://api.krishinet.in",
            "version": "1.0.0",
            "contact_email": "rotate@krishinet.in",
        },
    )

    # Request key rotation to key 2 signed by key 1
    rot_payload = {
        "new_public_key": pub_b64_2,
        "key_version": 2,
    }
    body_bytes = json.dumps(rot_payload, sort_keys=True).encode("utf-8")
    headers = _create_signed_headers(priv1, node_id, body_bytes)

    rot_res = await client.post(f"/registry/v1/nodes/{node_id}/rotate-key", content=body_bytes, headers=headers)
    assert rot_res.status_code == 200
    data = rot_res.json()
    assert data["key_version"] == 2
    assert "grace_period_expires_at" in data

    # Verify both keys are in node details
    detail_res = await client.get(f"/registry/v1/nodes/{node_id}")
    assert detail_res.status_code == 200
    keys = detail_res.json()["keys"]
    assert len(keys) == 2
    assert any(k["status"] == "active" and k["key_version"] == 2 for k in keys)
    assert any(k["status"] == "grace_period" and k["key_version"] == 1 for k in keys)
