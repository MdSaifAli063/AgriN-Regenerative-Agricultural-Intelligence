import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "KrishiNet-BRICS Core"
        assert data["demo_mode"] is True


@pytest.mark.asyncio
async def test_list_brics_countries():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/countries")
        assert response.status_code == 200
        countries = response.json()
        assert len(countries) >= 3
        codes = [c["code"] for c in countries]
        assert "IND" in codes
        assert "BRA" in codes
        assert "ZAF" in codes


@pytest.mark.asyncio
async def test_list_farms_and_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch user farms
        response = await client.get("/api/v1/farms")
        assert response.status_code == 200
        farms = response.json()
        assert len(farms) >= 1
        farm_id = farms[0]["id"]

        # 2. Fetch fields for that farm
        fields_resp = await client.get(f"/api/v1/farms/{farm_id}/fields")
        assert fields_resp.status_code == 200
        fields = fields_resp.json()
        assert len(fields) >= 1
        field_id = fields[0]["id"]

        # 3. Fetch satellite 90-day timeseries
        sat_resp = await client.get(f"/api/v1/fields/{field_id}/satellite?days=90")
        assert sat_resp.status_code == 200
        sat_data = sat_resp.json()
        assert len(sat_data) >= 5

        # 4. Fetch soil profile & score
        soil_resp = await client.get(f"/api/v1/fields/{field_id}/soil")
        assert soil_resp.status_code == 200
        soil_data = soil_resp.json()
        assert soil_data["soil_health_score"] > 0
        assert "interpretation" in soil_data["score_interpretation"].lower() or len(soil_data["score_interpretation"]) > 0

        # 5. Fetch weather forecast
        weather_resp = await client.get(f"/api/v1/fields/{field_id}/weather")
        assert weather_resp.status_code == 200
        weather_data = weather_resp.json()
        assert len(weather_data) == 7
