import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.config import settings
from app.core.security import create_dev_token


@pytest.mark.asyncio
async def test_farmer_can_access_own_farm():
    """Validates that a farmer can retrieve their own farm."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create token for Indian demo farmer
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/farms/farm-ind-vidarbha-01", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "farm-ind-vidarbha-01"
        assert data["country_iso"] == "IND"


@pytest.mark.asyncio
async def test_farmer_cross_access_blocked():
    """Validates that Farmer A cannot access Farmer B's farm (403 Forbidden)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Indian farmer attempting to access Brazilian farm
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/farms/farm-bra-sorriso-02", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_extension_officer_can_view_domestic_farms():
    """Validates that an Indian extension officer can view Indian farms."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-officer-ind-004",
            "role": "extension_officer",
            "country": "IND",
            "name": "Dr. Priya Sharma",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/farms/farm-ind-vidarbha-01", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == "farm-ind-vidarbha-01"


@pytest.mark.asyncio
async def test_extension_officer_cross_border_access_forbidden():
    """Validates that an Indian extension officer cannot inspect farms in Brazil."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-officer-ind-004",
            "role": "extension_officer",
            "country": "IND",
            "name": "Dr. Priya Sharma",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/farms/farm-bra-sorriso-02", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_government_admin_has_broad_access():
    """Validates that Government Admin role can access any farm."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-admin-ind-005",
            "role": "government_admin",
            "country": "IND",
            "name": "Rajesh Kumar",
        })
        headers = {"Authorization": f"Bearer {token}"}
        # Admin can view India and South Africa farms
        resp_ind = await client.get("/api/v1/farms/farm-ind-vidarbha-01", headers=headers)
        assert resp_ind.status_code == 200

        resp_zaf = await client.get("/api/v1/farms/farm-zaf-bothaville-03", headers=headers)
        assert resp_zaf.status_code == 200


@pytest.mark.asyncio
async def test_researcher_cannot_edit_farms():
    """Validates that Researcher role cannot update farm records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-researcher-bra-006",
            "role": "researcher",
            "country": "BRA",
            "name": "Dr. Carlos Mendez",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            "/api/v1/farms/farm-ind-vidarbha-01",
            json={"farm_name": "Unauthorized Renaming Attempt"},
            headers=headers,
        )
        # Researcher is not the owner of farm-ind-vidarbha-01
        assert resp.status_code in [403, 404]


@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected():
    """Validates that malformed or forged tokens are rejected with 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid.malformed.jwttoken"}
        resp = await client.get("/api/v1/farms/farm-ind-vidarbha-01", headers=headers)
        assert resp.status_code == 401
