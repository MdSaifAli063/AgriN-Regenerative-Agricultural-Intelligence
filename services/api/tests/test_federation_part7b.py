"""
KrishiNet-BRICS - Node Federation Unit Tests (Part 7B).
Tests Sovereign Egress Gate, Agreement Enforcement, Inbound Segregated Tables,
Node Passport, and 'What leaves my country' Audit Report.
"""

import datetime
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.federation.egress_gate import (
    EgressGate,
    EgressGateViolation,
    scan_payload_for_leaks,
    check_k_anonymity_suppression,
)
from app.federation.identity import NodeIdentity
from app.federation.publisher import OutboundPublisher
from app.federation.sync import InboundSyncService
from app.main import create_app
from app.models.federation import (
    EgressAuditLog,
    ExternalModelCard,
    ExternalOutbreakAggregate,
    FederationAgreement,
)

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
async def app_client(db_session):
    from app.core.deps import get_db
    from app.core.security import get_current_user
    from app.models.user import User
    
    app = create_app()

    mock_admin = User(
        id="test-admin-01",
        country_iso="IND",
        full_name="Dr. Policy Admin",
        phone_number="+919876543210",
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


@pytest.mark.asyncio
async def test_egress_gate_pii_and_coordinate_guards(db_session):
    """Egress Gate must block farmer PII, cadastral polygons, and fine coordinates."""
    gate = EgressGate(db_session)

    # 1. Block PII
    pii_payload = {"disease": "rust", "farmer_name": "Ramesh Patel", "cases": 12}
    with pytest.raises(EgressGateViolation):
        await gate.evaluate_and_record("registry", "registry-01", "outbreak_aggregates", pii_payload)

    # 2. Block Fine GPS coordinates (> 2 decimal places)
    fine_coord_payload = {
        "features": [
            {
                "geometry": {"coordinates": [78.5982, 20.7453]},  # 4 decimals -> REJECT
                "properties": {"reported_cases": 15},
            }
        ]
    }
    with pytest.raises(EgressGateViolation):
        await gate.evaluate_and_record("registry", "registry-01", "outbreak_aggregates", fine_coord_payload)

    # 3. Block Sub-k Outbreak clusters (< 5 cases)
    sub_k_payload = {
        "features": [
            {
                "geometry": {"coordinates": [78.60, 20.75]},  # 2 decimals -> acceptable
                "properties": {"reported_cases": 2},          # < 5 -> REJECT
            }
        ]
    }
    with pytest.raises(EgressGateViolation):
        await gate.evaluate_and_record("registry", "registry-01", "outbreak_aggregates", sub_k_payload)


@pytest.mark.asyncio
async def test_egress_gate_dry_run_and_audit_logging(db_session):
    """Verifies that dry-run mode returns verdict without raising and records EgressAuditLog."""
    gate = EgressGate(db_session)

    valid_payload = {
        "features": [
            {
                "geometry": {"coordinates": [78.60, 20.75]},
                "properties": {"disease": "rice_blast", "reported_cases": 28},
            }
        ]
    }

    passed, reason, summary = await gate.evaluate_and_record(
        destination_type="registry",
        destination_id="brics-commons-registry-01",
        scope="outbreak_aggregates",
        payload=valid_payload,
        is_dry_run=True,
    )

    assert passed is True
    assert summary["feature_count"] == 1

    # Verify audit entry was written
    from sqlalchemy import select
    res = await db_session.execute(select(EgressAuditLog))
    logs = res.scalars().all()
    assert len(logs) == 1
    assert logs[0].is_dry_run is True
    assert logs[0].passed_egress_gate is True
    assert len(logs[0].payload_hash) == 64


@pytest.mark.asyncio
async def test_data_sharing_agreements_crud_and_enforcement(app_client, db_session):
    """Tests agreement lifecycle: create, list, accept, revoke, and peer gate check."""
    # 1. Propose agreement
    create_res = await app_client.post(
        "/api/v1/federation/agreements",
        json={
            "peer_node_id": "node-bra-embrapa-01",
            "peer_country_iso": "BRA",
            "title": "Bilateral Indo-Brazil Soybean Intelligence Pact",
            "scopes": ["outbreak_aggregates", "model_exchange"],
            "valid_days": 365,
            "terms_text": "Both nations agree to sovereign data residency and reciprocal model cards sharing.",
        },
    )
    assert create_res.status_code == 201
    agr = create_res.json()
    agr_id = agr["id"]
    assert agr["status"] == "active"
    assert "model_exchange" in agr["scopes"]

    # 2. Gate check for authorized peer scope
    gate = EgressGate(db_session)
    has_agr = await gate.verify_agreement("node-bra-embrapa-01", "model_exchange")
    assert has_agr is True

    # Gate check for unauthorized peer scope -> False
    has_unauth = await gate.verify_agreement("node-bra-embrapa-01", "climate_signatures")
    assert has_unauth is False

    # 3. Revoke agreement
    rev_res = await app_client.post(f"/api/v1/federation/agreements/{agr_id}/revoke")
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "revoked"

    # Now verify_agreement must return False
    has_revoked = await gate.verify_agreement("node-bra-embrapa-01", "model_exchange")
    assert has_revoked is False


@pytest.mark.asyncio
async def test_inbound_sync_segregated_external_tables(db_session):
    """Verifies that inbound sync stores foreign data into external_* tables only."""
    sync_service = InboundSyncService(db_session, registry_url="http://mock-registry")

    # 1. Sync external outbreaks
    outbreak_count = await sync_service.sync_external_outbreaks()
    assert outbreak_count == 2

    from sqlalchemy import select
    res_outbreak = await db_session.execute(select(ExternalOutbreakAggregate))
    outbreaks = res_outbreak.scalars().all()
    assert len(outbreaks) == 2
    assert any(o.origin_country_iso == "BRA" for o in outbreaks)
    assert any(o.disease_label == "soybean_rust" for o in outbreaks)

    # 2. Sync external models
    model_count = await sync_service.sync_external_models()
    assert model_count == 1

    res_models = await db_session.execute(select(ExternalModelCard))
    models = res_models.scalars().all()
    assert len(models) == 1
    assert models[0].origin_country_iso == "BRA"
    assert models[0].status == "candidate"


@pytest.mark.asyncio
async def test_node_passport_and_egress_report(app_client, db_session):
    """Tests GET /.well-known/agrin-node.json and GET /api/v1/federation/egress/report."""
    # 1. Node Passport
    passport_res = await app_client.get("/.well-known/agrin-node.json")
    assert passport_res.status_code == 200
    passport = passport_res.json()
    assert passport["node_id"] == settings.NODE_ID
    assert "OGC-STAC-1.0.0" in passport["standards_supported"]
    assert passport["data_policy"]["raw_data_residency"] == "100% on-soil"
    assert passport["data_policy"]["min_k_anonymity"] == 5

    # 2. Egress Report
    report_res = await app_client.get("/api/v1/federation/egress/report")
    assert report_res.status_code == 200
    rep = report_res.json()
    assert rep["node_id"] == settings.NODE_ID
    assert rep["zero_pii_confirmed"] is True
