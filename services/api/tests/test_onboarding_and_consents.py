import os
import sys
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.security import create_dev_token


@pytest.mark.asyncio
async def test_onboarding_success_flow():
    """Validates that a new farmer can complete the 60-second onboarding in a single transaction."""
    transport = ASGITransport(app=app)
    unique_suffix = str(uuid.uuid4())[:8]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": f"Farmer Test {unique_suffix}",
            "phone_number": f"+9199{unique_suffix}",
            "country_iso": "IND",
            "preferred_language": "hi",
            "farm_name": "New Greenfield Farm",
            "state_province": "Maharashtra",
            "village_district": "Akola",
            "field_name": "First Parcel",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [77.0735, 20.5810],
                        [77.0770, 20.5810],
                        [77.0770, 20.5835],
                        [77.0735, 20.5835],
                        [77.0735, 20.5810],
                    ]
                ],
            },
            "current_crop": "cotton",
            "irrigation_type": "rainfed",
            "share_anonymized_soil": True,
            "share_outbreak_telemetry": True,
            "participate_in_federated_learning": True,
        }
        resp = await client.post("/api/v1/onboarding", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "user_id" in data
        assert "farm_id" in data
        assert "field_id" in data
        assert data["area_hectares"] > 0


@pytest.mark.asyncio
async def test_onboarding_invalid_polygon_fails_fast():
    """Validates that an invalid polygon raises 422 Unprocessable Entity during onboarding."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": "Faulty Geo Farmer",
            "phone_number": "+918888800001",
            "country_iso": "IND",
            "farm_name": "Broken Geo Farm",
            "state_province": "Punjab",
            "field_name": "Broken Polygon",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    # Incomplete / degenerate geometry (less than 4 coordinates)
                    [
                        [77.0, 28.0],
                        [77.1, 28.1],
                    ]
                ],
            },
            "current_crop": "wheat",
        }
        resp = await client.post("/api/v1/onboarding", json=payload)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_onboarding_missing_required_fields():
    """Validates that missing mandatory fields are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing farm_name and boundary_geojson
        payload = {
            "full_name": "Incomplete Farmer",
            "phone_number": "+918888800002",
            "country_iso": "IND",
        }
        resp = await client.post("/api/v1/onboarding", json=payload)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_farmer_consent():
    """Validates retrieval of active data-sharing consent preferences."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/consents", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "share_anonymized_soil" in data
        assert "share_outbreak_telemetry" in data
        assert "participate_in_federated_learning" in data


@pytest.mark.asyncio
async def test_update_farmer_consent():
    """Validates updating granular consent flags."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        update_payload = {
            "share_anonymized_soil": False,
            "share_outbreak_telemetry": True,
            "participate_in_federated_learning": False,
        }
        resp = await client.post("/api/v1/consents", json=update_payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_anonymized_soil"] is False
        assert data["share_outbreak_telemetry"] is True
        assert data["participate_in_federated_learning"] is False


@pytest.mark.asyncio
async def test_revoke_specific_consent_scope():
    """Validates explicit revocation of a specific consent scope via DELETE /api/v1/consents/{scope}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.delete("/api/v1/consents/soil", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_anonymized_soil"] is False
