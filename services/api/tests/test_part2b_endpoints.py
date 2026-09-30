import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Liveness
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

        # Readiness
        resp = await client.get("/health/ready")
        assert resp.status_code in [200, 503]
        data = resp.json()
        assert "components" in data

        # Demo Mode
        resp = await client.get("/health/demo-mode")
        assert resp.status_code == 200
        assert resp.json()["demo_mode"] is True


@pytest.mark.asyncio
async def test_auth_dev_login_and_roles():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Roles
        resp = await client.get("/api/v1/auth/roles")
        assert resp.status_code == 200
        roles = resp.json()["roles"]
        assert "farmer" in roles
        assert "extension_officer" in roles

        # Dev Login
        login_resp = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "user_id": "test-farmer-01",
                "role": "farmer",
                "country_iso": "IND",
                "full_name": "Ramesh Patil",
                "phone_number": "+919876543210",
            },
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # Profile with token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["id"] == "test-farmer-01"


@pytest.mark.asyncio
async def test_onboarding_60_second_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": "Sipho Nkosi",
            "phone_number": "+27821234567",
            "country_iso": "ZAF",
            "preferred_language": "en",
            "farm_name": "Bothaville Maize Parcel",
            "state_province": "Free State",
            "village_district": "Lejweleputswa",
            "field_name": "North Pivot",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [26.6150, -27.3850],
                        [26.6250, -27.3850],
                        [26.6250, -27.3780],
                        [26.6150, -27.3780],
                        [26.6150, -27.3850],
                    ]
                ],
            },
            "current_crop": "maize",
            "irrigation_type": "sprinkler",
            "share_anonymized_soil": True,
            "share_outbreak_telemetry": True,
            "participate_in_federated_learning": True,
        }

        resp = await client.post("/api/v1/onboarding", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["area_hectares"] > 0
        assert "user_id" in data
        assert "farm_id" in data
        assert "field_id" in data


@pytest.mark.asyncio
async def test_presign_upload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "image/jpeg", "file_size_bytes": 1024 * 500},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "upload_url" in data
        assert data["object_key"].startswith("uploads/")
