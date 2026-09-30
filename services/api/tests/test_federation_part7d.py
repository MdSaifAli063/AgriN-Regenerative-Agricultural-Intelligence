"""
Part 7D Tests – Model Hub: Registration, Evaluation, Promotion Gate, Presigned URLs.

Tests:
  1.  Hub entry registration creates candidate with Ed25519 signature.
  2.  Card signature is verifiable with node's own public key.
  3.  Submit evaluation below threshold → gate fails, entry stays candidate.
  4.  Submit evaluation above threshold → gate passes.
  5.  Promote without passing evaluation raises ValueError.
  6.  Promote with passing evaluation succeeds and creates promotion event.
  7.  Reject transitions entry to rejected with event.
  8.  Deprecate transitions promoted entry to deprecated.
  9.  Promotion event history is ordered newest-first.
 10.  Presigned URL generation returns URL containing bucket and object_key (dev mode).
 11.  GET /api/v1/model-hub lists catalog with thresholds in response.
 12.  POST /api/v1/model-hub registers entry (API level).
 13.  GET /api/v1/model-hub/{id}/download-url returns URL.
 14.  POST /api/v1/model-hub/{id}/evaluations returns gate detail.
 15.  POST /api/v1/model-hub/{id}/promote enforces gate (returns 422 if no passing eval).
 16.  POST /api/v1/model-hub/verify-signature returns valid=True for correct signature.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "src"))
sys.path.insert(0, str(REPO_ROOT / "services" / "registry" / "src"))

from app.db.base import Base
from app.main import create_app
from app.core.deps import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.brics import MLModel, ModelCard
from app.models.model_hub import ModelHubEntry, ModelEvaluation, ModelPromotionEvent
from app.federation.model_hub_service import ModelHubService, PromotionGate
from app.federation.identity import NodeIdentity

pytestmark = pytest.mark.asyncio

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_card(db_session) -> ModelCard:
    """Seed a minimal MLModel + ModelCard so FK constraints pass."""
    model = MLModel(
        id=str(uuid.uuid4()),
        model_name="MobileNetV3-Disease-BRICS",
        task_type="disease_classifier",
    )
    db_session.add(model)
    await db_session.flush()

    card = ModelCard(
        id=str(uuid.uuid4()),
        model_id=model.id,
        version_tag="v3.2",
        accuracy_score=0.88,
        training_data_summary="BRICS held-out test set 2025-Q4",
        bias_limitations="Limited to wheat, rice, maize; no night photography.",
        s3_weights_uri="s3://krishinet-assets/models/mnv3/v3.2/weights.tflite",
        weights_sha256="a" * 64,
        card_markdown="# MobileNetV3-Disease-BRICS\nFederated disease classifier.",
    )
    db_session.add(card)
    await db_session.commit()
    return card


@pytest_asyncio.fixture
async def hub_service(db_session) -> ModelHubService:
    return ModelHubService(db_session)


@pytest_asyncio.fixture
async def app_client(db_session):
    app = create_app()

    mock_admin = User(
        id="admin-7d-test",
        country_iso="IND",
        full_name="Model Hub Admin",
        phone_number="+919000007400",
        role="government_admin",
    )

    async def override_db():
        yield db_session

    async def override_user():
        return mock_admin

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ── Service-layer tests ───────────────────────────────────────────────────────

async def test_register_entry_creates_candidate(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key=f"models/{seeded_card.id}/weights.tflite",
        size_bytes=4_500_000,
        weights_sha256="b" * 64,
        task_type="disease_classifier",
        crop_coverage=["wheat", "rice"],
        card_json={"model": "MobileNetV3", "version": "3.2"},
    )
    assert entry.status == "candidate"
    assert entry.node_id is not None
    assert len(entry.card_signature_hex) > 0
    assert entry.card_signed_by_node == entry.node_id


async def test_card_signature_is_verifiable(hub_service, seeded_card):
    card_json = {"model": "MobileNetV3", "version": "3.2", "task": "disease_classifier"}
    sig_hex = hub_service.sign_card_json(card_json)
    assert len(sig_hex) == 128  # Ed25519 sig = 64 bytes = 128 hex chars

    # Export the node's public key PEM and verify
    identity = hub_service._get_identity()
    from cryptography.hazmat.primitives import serialization as ser
    pub_pem = identity.public_key.public_bytes(
        encoding=ser.Encoding.PEM,
        format=ser.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    valid = ModelHubService.verify_card_signature(card_json, sig_hex, pub_pem)
    assert valid is True

    # Tampered payload should fail
    tampered = {**card_json, "version": "9.9"}
    invalid = ModelHubService.verify_card_signature(tampered, sig_hex, pub_pem)
    assert invalid is False


async def test_promotion_gate_fail_below_threshold(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test/weights.tflite",
        size_bytes=1_000_000,
        weights_sha256="c" * 64,
        task_type="disease_classifier",
        crop_coverage=["wheat"],
        card_json={},
    )
    ev = await hub_service.submit_evaluation(
        hub_entry_id=entry.id,
        eval_dataset="IND-wheat-holdout-v3",
        accuracy=0.70,        # Below GATE_MIN_ACCURACY (0.80)
        f1_macro=0.65,        # Below GATE_MIN_F1_MACRO (0.75)
        precision=0.72,
        recall=0.68,
        min_subgroup_f1=0.60,
        max_demographic_parity_gap=0.10,
        fairness_pass=False,
    )
    assert ev.gate_passed is False
    assert ev.gate_detail["accuracy"]["pass"] is False
    assert ev.gate_detail["f1_macro"]["pass"] is False


async def test_promotion_gate_pass_above_threshold(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test2/weights.tflite",
        size_bytes=4_200_000,
        weights_sha256="d" * 64,
        task_type="disease_classifier",
        crop_coverage=["wheat", "maize"],
        card_json={},
    )
    ev = await hub_service.submit_evaluation(
        hub_entry_id=entry.id,
        eval_dataset="IND-wheat-holdout-v3",
        accuracy=0.92,
        f1_macro=0.88,
        precision=0.90,
        recall=0.86,
        min_subgroup_f1=0.82,
        max_demographic_parity_gap=0.05,
        fairness_pass=True,
        inference_ms_p95=180.0,
        peak_ram_mb=64.0,
    )
    assert ev.gate_passed is True
    assert all(v["pass"] for v in ev.gate_detail.values() if isinstance(v, dict) and "pass" in v)


async def test_promote_without_passing_eval_raises(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test3/weights.tflite",
        size_bytes=1_000_000,
        weights_sha256="e" * 64,
        task_type="disease_classifier",
        crop_coverage=[],
        card_json={},
    )
    # No evaluation submitted → promotion must fail
    with pytest.raises(ValueError, match="no gate-passing evaluation"):
        await hub_service.promote(
            hub_entry_id=entry.id,
            reviewer_role="government_admin",
            rationale="Trying to promote without eval.",
            reviewer_country_iso="IND",
        )


async def test_promote_with_passing_eval_succeeds(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test4/weights.tflite",
        size_bytes=4_000_000,
        weights_sha256="f" * 64,
        task_type="disease_classifier",
        crop_coverage=["rice"],
        card_json={},
    )
    await hub_service.submit_evaluation(
        hub_entry_id=entry.id,
        eval_dataset="IND-rice-holdout-v2",
        accuracy=0.91,
        f1_macro=0.87,
        precision=0.89,
        recall=0.85,
        min_subgroup_f1=0.80,
        max_demographic_parity_gap=0.06,
        fairness_pass=True,
    )
    promoted = await hub_service.promote(
        hub_entry_id=entry.id,
        reviewer_role="government_admin",
        rationale="Passed all gates; ready for production.",
        reviewer_country_iso="IND",
    )
    assert promoted.status == "promoted"
    assert promoted.promoted_at is not None

    history = await hub_service.get_promotion_history(entry.id)
    assert len(history) == 1
    assert history[0].action == "promote"
    assert len(history[0].signature_hex) > 0


async def test_reject_entry(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test5/weights.tflite",
        size_bytes=1_000_000,
        weights_sha256="a0" * 32,
        task_type="ndvi_estimator",
        crop_coverage=["soybean"],
        card_json={},
    )
    rejected = await hub_service.reject(
        hub_entry_id=entry.id,
        reviewer_role="government_admin",
        rationale="Model has unacceptable bias on small-holder farms.",
        reviewer_country_iso="IND",
    )
    assert rejected.status == "rejected"
    history = await hub_service.get_promotion_history(entry.id)
    assert history[0].action == "reject"


async def test_deprecate_promoted_entry(hub_service, seeded_card):
    entry = await hub_service.register_entry(
        model_card_id=seeded_card.id,
        bucket="krishinet-assets",
        object_key="models/test6/weights.tflite",
        size_bytes=3_500_000,
        weights_sha256="b0" * 32,
        task_type="disease_classifier",
        crop_coverage=["maize"],
        card_json={},
    )
    await hub_service.submit_evaluation(
        hub_entry_id=entry.id,
        eval_dataset="BRA-maize-holdout-v1",
        accuracy=0.84,
        f1_macro=0.79,
        precision=0.83,
        recall=0.76,
        min_subgroup_f1=0.70,
        max_demographic_parity_gap=0.08,
        fairness_pass=True,
    )
    await hub_service.promote(
        hub_entry_id=entry.id,
        reviewer_role="government_admin",
        rationale="Initial production release.",
        reviewer_country_iso="BRA",
    )
    deprecated = await hub_service.deprecate(
        hub_entry_id=entry.id,
        reviewer_role="government_admin",
        rationale="Superseded by v4.0 with 95% accuracy.",
        reviewer_country_iso="BRA",
    )
    assert deprecated.status == "deprecated"
    assert deprecated.deprecated_at is not None


async def test_presigned_url_dev_fallback(hub_service):
    url = ModelHubService.generate_presigned_url(
        object_key="models/abc/weights.tflite",
        expires_seconds=3600,
    )
    assert "models/abc/weights.tflite" in url
    assert "3600" in url


# ── API-level tests ──────────────────────────────────────────────────────────

async def test_api_list_catalog(app_client):
    r = await app_client.get("/api/v1/model-hub")
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    assert "promotion_gate_thresholds" in body
    assert body["promotion_gate_thresholds"]["min_accuracy"] == 0.80


async def test_api_register_and_download(app_client, seeded_card):
    # Register
    payload = {
        "model_card_id": seeded_card.id,
        "bucket": "krishinet-assets",
        "object_key": f"models/{seeded_card.id}/weights.tflite",
        "size_bytes": 4_000_000,
        "weights_sha256": "c0" * 32,
        "task_type": "disease_classifier",
        "crop_coverage": ["wheat"],
        "card_json": {"model": "MobileNetV3", "version": "3.2"},
    }
    r = await app_client.post("/api/v1/model-hub", json=payload)
    assert r.status_code == 201, r.text
    entry_id = r.json()["id"]
    assert r.json()["status"] == "candidate"
    assert r.json()["card_signature_hex"] != ""

    # Download URL (admin can download candidates)
    r2 = await app_client.get(f"/api/v1/model-hub/{entry_id}/download-url")
    assert r2.status_code == 200
    body = r2.json()
    assert "download_url" in body
    assert "weights_sha256" in body
    assert body["expires_seconds"] == 3600


async def test_api_submit_eval_and_promote(app_client, seeded_card):
    # Register
    r = await app_client.post("/api/v1/model-hub", json={
        "model_card_id": seeded_card.id,
        "bucket": "krishinet-assets",
        "object_key": "models/api-test/weights.tflite",
        "size_bytes": 3_800_000,
        "weights_sha256": "d0" * 32,
        "task_type": "disease_classifier",
        "crop_coverage": ["rice", "maize"],
        "card_json": {},
    })
    entry_id = r.json()["id"]

    # Submit failing eval
    eval_payload = {
        "eval_dataset": "IND-rice-v3",
        "accuracy": 0.72,
        "f1_macro": 0.68,
        "precision": 0.70,
        "recall": 0.66,
        "min_subgroup_f1": 0.60,
        "max_demographic_parity_gap": 0.20,
        "fairness_pass": False,
    }
    re = await app_client.post(f"/api/v1/model-hub/{entry_id}/evaluations", json=eval_payload)
    assert re.status_code == 201
    assert re.json()["gate_passed"] is False

    # Promote without passing eval → 422
    rp = await app_client.post(
        f"/api/v1/model-hub/{entry_id}/promote",
        json={"rationale": "Force promote without passing gate."},
    )
    assert rp.status_code == 422

    # Submit passing eval
    passing_eval = {
        "eval_dataset": "IND-rice-v3",
        "accuracy": 0.93,
        "f1_macro": 0.90,
        "precision": 0.91,
        "recall": 0.89,
        "min_subgroup_f1": 0.85,
        "max_demographic_parity_gap": 0.04,
        "fairness_pass": True,
        "inference_ms_p95": 160.0,
        "peak_ram_mb": 55.0,
    }
    re2 = await app_client.post(f"/api/v1/model-hub/{entry_id}/evaluations", json=passing_eval)
    assert re2.json()["gate_passed"] is True

    # Now promote
    rp2 = await app_client.post(
        f"/api/v1/model-hub/{entry_id}/promote",
        json={"rationale": "All gates passed. Ready for BRICS deployment."},
    )
    assert rp2.status_code == 200
    assert rp2.json()["entry"]["status"] == "promoted"

    # Check history
    rh = await app_client.get(f"/api/v1/model-hub/{entry_id}/history")
    assert rh.status_code == 200
    events = rh.json()["events"]
    assert len(events) >= 1
    assert events[0]["action"] == "promote"
    assert events[0]["signature_hex"] != ""


async def test_api_verify_signature_valid(app_client):
    import base64
    from cryptography.hazmat.primitives import serialization as ser

    # Generate a fresh identity for signing
    identity = NodeIdentity.generate("test-node-sig")
    card = {"model": "TestNet", "version": "1.0"}
    canonical = json.dumps(card, sort_keys=True, separators=(",", ":")).encode()
    sig_b64 = identity.sign_message(canonical)
    sig_bytes = base64.b64decode(sig_b64)
    sig_hex = sig_bytes.hex()

    pub_pem = identity.public_key.public_bytes(
        encoding=ser.Encoding.PEM,
        format=ser.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    r = await app_client.post("/api/v1/model-hub/verify-signature", json={
        "card_json": card,
        "signature_hex": sig_hex,
        "public_key_pem": pub_pem,
    })
    assert r.status_code == 200
    assert r.json()["valid"] is True


async def test_api_verify_signature_invalid(app_client):
    import base64
    from cryptography.hazmat.primitives import serialization as ser

    identity = NodeIdentity.generate("test-node-sig2")
    card_signed = {"model": "TestNet", "version": "1.0"}
    canonical = json.dumps(card_signed, sort_keys=True, separators=(",", ":")).encode()
    sig_b64 = identity.sign_message(canonical)
    sig_bytes = base64.b64decode(sig_b64)
    sig_hex = sig_bytes.hex()

    pub_pem = identity.public_key.public_bytes(
        encoding=ser.Encoding.PEM,
        format=ser.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    # Submit with tampered card – signature will not match
    r = await app_client.post("/api/v1/model-hub/verify-signature", json={
        "card_json": {"model": "EVIL_NET", "version": "99.9"},
        "signature_hex": sig_hex,
        "public_key_pem": pub_pem,
    })
    assert r.status_code == 200
    assert r.json()["valid"] is False

