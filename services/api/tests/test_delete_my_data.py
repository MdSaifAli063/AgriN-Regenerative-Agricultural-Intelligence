"""
Tests for Data Retention Policies and the 'Delete My Data' (Right to be Forgotten) Procedure.
Verifies end-to-end erasure across DB, object storage, messaging sessions, and audit log scrubbing.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import uuid
from app.models.advisory import Advisory
from app.models.audit import AuditLog, Notification
from app.models.disease import DiseaseDetection
from app.models.farm import Farm, Field
from app.models.messaging import InboundMessage, MessageSession, OutboundMessage
from app.models.user import Consent, User
from app.services.privacy.retention import DataRetentionManager
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_end_to_end_delete_my_data_procedure(db_session):
    """
    Creates full farmer dataset across all tables and verifies complete cascading erasure,
    MinIO asset removal, and audit log anonymization.
    """
    user_id = str(uuid.uuid4())
    farm_id = str(uuid.uuid4())
    field_id = str(uuid.uuid4())
    advisory_id = str(uuid.uuid4())
    detection_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    random_suffix = uuid.uuid4().hex[:8]
    phone_number = f"+9199{uuid.uuid4().int % 100000000:08d}"
    phone_hash = f"mock_hash_{random_suffix}"

    # 1. Seed user
    user = User(
        id=user_id,
        email=f"farmer_{random_suffix}@example.com",
        full_name="Retention Test Farmer",
        phone_number=phone_number,
        role="farmer",
        country_iso="IND",
        is_verified=True,
    )
    db_session.add(user)

    # 2. Seed consent
    consent = Consent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        share_anonymized_soil=True,
        share_outbreak_telemetry=True,
        participate_in_federated_learning=True,
    )
    db_session.add(consent)

    # 3. Seed Farm & Field
    farm = Farm(
        id=farm_id,
        user_id=user_id,
        farm_name="Retention Farm",
        state_province="Maharashtra",
        country_iso="IND",
    )
    db_session.add(farm)

    field = Field(
        id=field_id,
        farm_id=farm_id,
        field_name="Retention Field",
        boundary_geojson={"type": "Polygon", "coordinates": [[[78.0, 20.0], [78.1, 20.0], [78.1, 20.1], [78.0, 20.0]]]},
        centroid_lat=20.0,
        centroid_lon=78.0,
        area_hectares=2.5,
        current_crop="Cotton",
    )
    db_session.add(field)

    # 4. Seed Advisory
    adv = Advisory(
        id=advisory_id,
        field_id=field_id,
        confidence_score=0.88,
        top_3_crops=[{"crop": "Cotton", "score": 92}],
        regenerative_practices=[{"name": "composting"}],
        sowing_window={"optimal": "June 15 - July 10"},
        irrigation_schedule={"frequency": "Weekly"},
        organic_fertilizer_plan={"type": "FYM"},
        explainability_signals={"soil_ph": 6.8},
        disclaimer_note="AI guidance, not a substitute for extension officer.",
        prompt_version="v1.0.0",
        engine_mode="rules",
        language="en",
        execution_trace={},
        full_advisory_json={"summary": "Composting recommended"},
    )
    db_session.add(adv)

    # 5. Seed Disease Detection
    detection = DiseaseDetection(
        id=detection_id,
        farmer_id=user_id,
        field_id=field_id,
        image_s3_uri="s3://krishinet-assets/uploads/2026-09-30/test_leaf_disease.jpg",
        ensemble_prediction={"class": "healthy", "confidence": 0.95},
        primary_disease_name="healthy",
        organic_treatment="Neem oil spray if symptoms emerge",
        latitude=20.0,
        longitude=78.0,
    )
    db_session.add(detection)

    # 6. Seed Messaging Session & Messages
    session = MessageSession(
        id=session_id,
        phone_number=phone_number,
        phone_hash=phone_hash,
        linked_user_id=user_id,
        channel="whatsapp",
        current_state="MENU",
    )
    db_session.add(session)

    inbound = InboundMessage(
        id=str(uuid.uuid4()),
        provider="twilio",
        provider_message_id=f"wamid_{uuid.uuid4().hex[:12]}",
        from_phone_hash=phone_hash,
        channel="whatsapp",
        body="Hello advisory",
        received_at=datetime.now(timezone.utc),
    )
    db_session.add(inbound)

    outbound = OutboundMessage(
        id=str(uuid.uuid4()),
        provider="twilio",
        provider_message_id=f"SM_{uuid.uuid4().hex[:12]}",
        to_phone_hash=phone_hash,
        channel="whatsapp",
        body="Welcome to KrishiNet",
        status="sent",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(outbound)

    # 7. Seed Notification & AuditLog
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title="Weather Alert",
        body="Rain forecast",
        notification_type="frost_warning",
    )
    db_session.add(notif)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action="LOGIN",
        resource_type="auth",
    )
    db_session.add(audit)

    await db_session.commit()

    # Verify seed data exists
    u_chk = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    assert u_chk is not None

    # 8. Execute Delete My Data
    mock_redis = AsyncMock()
    with patch("app.services.storage.storage_service.delete_objects", return_value=1) as mock_minio:
        result = await DataRetentionManager.delete_farmer_data(
            db=db_session,
            user_id=user_id,
            redis_client=mock_redis,
        )

        assert result["status"] == "erased"
        assert result["user_id"] == user_id
        mock_minio.assert_called_once()
        mock_redis.delete.assert_called()

    # 9. Verify DB records are completely wiped
    u_after = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    assert u_after is None

    farm_after = (await db_session.execute(select(Farm).where(Farm.id == farm_id))).scalar_one_or_none()
    assert farm_after is None

    field_after = (await db_session.execute(select(Field).where(Field.id == field_id))).scalar_one_or_none()
    assert field_after is None

    adv_after = (await db_session.execute(select(Advisory).where(Advisory.id == advisory_id))).scalar_one_or_none()
    assert adv_after is None

    det_after = (await db_session.execute(select(DiseaseDetection).where(DiseaseDetection.id == detection_id))).scalar_one_or_none()
    assert det_after is None

    sess_after = (await db_session.execute(select(MessageSession).where(MessageSession.id == session_id))).scalar_one_or_none()
    assert sess_after is None

    notif_after = (await db_session.execute(select(Notification).where(Notification.id == notif.id))).scalar_one_or_none()
    assert notif_after is None

    # 10. Verify Audit Log was anonymized (user_id is None, record remains for tamper-evident ledger)
    audit_after = (await db_session.execute(select(AuditLog).where(AuditLog.id == audit.id))).scalar_one_or_none()
    assert audit_after is not None
    assert audit_after.user_id is None


@pytest.mark.asyncio
async def test_purge_expired_messages(db_session):
    """Verifies that messages older than the retention threshold are deleted while recent messages are kept."""
    session_id = str(uuid.uuid4())
    phone_hash = "retention_msg_test_hash"

    # Seed session
    session = MessageSession(
        id=session_id,
        phone_number="+918888877777",
        phone_hash=phone_hash,
        channel="sms",
        current_state="MENU",
    )
    db_session.add(session)

    # Old message (45 days ago)
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    old_inbound = InboundMessage(
        id=str(uuid.uuid4()),
        provider="simulator",
        provider_message_id=f"sim_in_{uuid.uuid4().hex[:10]}",
        from_phone_hash=phone_hash,
        channel="sms",
        body="Old message from 45 days ago",
        received_at=old_time,
    )
    old_outbound = OutboundMessage(
        id=str(uuid.uuid4()),
        provider="simulator",
        provider_message_id=f"sim_out_{uuid.uuid4().hex[:10]}",
        to_phone_hash=phone_hash,
        channel="sms",
        body="Old reply",
        status="delivered",
        created_at=old_time,
    )
    db_session.add(old_inbound)
    db_session.add(old_outbound)

    # Fresh message (2 days ago)
    fresh_time = datetime.now(timezone.utc) - timedelta(days=2)
    fresh_inbound = InboundMessage(
        id=str(uuid.uuid4()),
        provider="simulator",
        provider_message_id=f"sim_in_{uuid.uuid4().hex[:10]}",
        from_phone_hash=phone_hash,
        channel="sms",
        body="Recent message",
        received_at=fresh_time,
    )
    fresh_outbound = OutboundMessage(
        id=str(uuid.uuid4()),
        provider="simulator",
        provider_message_id=f"sim_out_{uuid.uuid4().hex[:10]}",
        to_phone_hash=phone_hash,
        channel="sms",
        body="Recent reply",
        status="delivered",
        created_at=fresh_time,
    )
    db_session.add(fresh_inbound)
    db_session.add(fresh_outbound)
    await db_session.commit()

    # Execute 30-day retention purge
    purged = await DataRetentionManager.purge_expired_messages(db=db_session, retention_days=30)
    assert purged["inbound_purged"] >= 1
    assert purged["outbound_purged"] >= 1

    # Verify old messages are gone
    old_in_chk = (await db_session.execute(select(InboundMessage).where(InboundMessage.id == old_inbound.id))).scalar_one_or_none()
    assert old_in_chk is None

    old_out_chk = (await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == old_outbound.id))).scalar_one_or_none()
    assert old_out_chk is None

    # Verify fresh messages remain
    fresh_in_chk = (await db_session.execute(select(InboundMessage).where(InboundMessage.id == fresh_inbound.id))).scalar_one_or_none()
    assert fresh_in_chk is not None

    fresh_out_chk = (await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == fresh_outbound.id))).scalar_one_or_none()
    assert fresh_out_chk is not None


@pytest.mark.asyncio
async def test_delete_my_data_api_endpoint(async_client, db_session):
    """Verifies that calling POST /api/v1/consents/delete-my-data successfully triggers erasure."""
    from app.core.security import get_current_user
    from app.main import app

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=f"api_farmer_{user_id[:8]}@example.com",
        full_name="API Farmer For Deletion",
        role="farmer",
        country_iso="IND",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Override get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        res = await async_client.post("/api/v1/consents/delete-my-data")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "erased"
        assert data["user_id"] == user_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)

