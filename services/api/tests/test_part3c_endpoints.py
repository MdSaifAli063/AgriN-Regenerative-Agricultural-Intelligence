"""
KrishiNet-BRICS - Phase 3 Part 3C Endpoint Integration & RBAC Test Suite.

Validates:
  1. GET /api/v1/fields/{id}/intelligence (full consolidated snapshot with provenance)
  2. RBAC ownership isolation:
     - Farmer A cannot read Farmer B's field intelligence (403 Forbidden)
     - Extension Officer can read domestic fields but blocked cross-border (403 Forbidden)
     - Researcher can inspect cross-border fields (200 OK)
     - Government Admin has broad access across all fields (200 OK)
  3. Sub-endpoints:
     - GET /api/v1/fields/{id}/satellite
     - GET /api/v1/fields/{id}/satellite/tiles-info
     - GET /api/v1/fields/{id}/soil
     - GET /api/v1/fields/{id}/weather
  4. POST /api/v1/fields/{id}/intelligence/refresh (202 Accepted + Celery task_id flow)
  5. GET /api/v1/intelligence/crop-thresholds (Public crop registry)
  6. GET /health/providers (External provider telemetry status)
"""

import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.security import create_dev_token


# ============================================================================
# 1. CONSOLIDATED INTELLIGENCE ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_farmer_can_get_field_intelligence():
    """Validates that a farmer can retrieve complete intelligence snapshot for their own field."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/intelligence", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["field_id"] == "field-ind-vidarbha-cotton-01"
        assert data["field_health_status"] in ["healthy", "watch", "risk"]
        assert len(data["driving_factors"]) >= 1

        # Check all 3 sub-payloads are present
        assert "satellite" in data
        assert "soil" in data
        assert "weather" in data
        assert data["satellite"]["provenance"]["mode"] in ["live", "cache", "demo"]
        assert data["soil"]["provenance"]["mode"] in ["live", "cache", "demo"]
        assert data["weather"]["provenance"]["mode"] in ["live", "cache", "demo"]


@pytest.mark.asyncio
async def test_intelligence_nonexistent_field_returns_404():
    """Validates that querying a non-existent field returns 404 EntityNotFoundException."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/nonexistent-field-uuid/intelligence", headers=headers)
        assert resp.status_code == 404
        err_msg = resp.json().get("error", {}).get("message", "") or resp.json().get("detail", "")
        assert "not found" in err_msg.lower()


# ============================================================================
# 2. RBAC & CROSS-BORDER SOVEREIGNTY CHECKS
# ============================================================================

@pytest.mark.asyncio
async def test_farmer_cross_access_to_other_field_forbidden():
    """Validates that an Indian farmer cannot inspect Brazilian field intelligence (403 Forbidden)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Indian farmer attempting to inspect Brazilian farm's field
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-bra-sorriso-soy-02/intelligence", headers=headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_extension_officer_domestic_vs_cross_border():
    """Validates domestic extension officer access vs cross-border restriction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-officer-ind-004",
            "role": "extension_officer",
            "country": "IND",
            "name": "Dr. Priya Sharma",
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Domestic Indian field: 200 OK
        resp_dom = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/intelligence", headers=headers)
        assert resp_dom.status_code == 200

        # Cross-border Brazilian field: 403 Forbidden
        resp_cross = await client.get("/api/v1/fields/field-bra-sorriso-soy-02/intelligence", headers=headers)
        assert resp_cross.status_code == 403


@pytest.mark.asyncio
async def test_researcher_and_admin_cross_border_access():
    """Validates that Agronomy Researchers and Government Admins have legitimate read access."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Brazilian researcher inspecting Indian field
        res_token = create_dev_token({
            "sub": "user-research-bra-006",
            "role": "researcher",
            "country": "BRA",
            "name": "Dr. Carlos Mendez",
        })
        headers_res = {"Authorization": f"Bearer {res_token}"}
        resp_res = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/intelligence", headers=headers_res)
        assert resp_res.status_code == 200

        # Indian Admin inspecting South African field
        adm_token = create_dev_token({
            "sub": "user-admin-ind-005",
            "role": "government_admin",
            "country": "IND",
            "name": "Rajesh Kumar",
        })
        headers_adm = {"Authorization": f"Bearer {adm_token}"}
        resp_adm = await client.get("/api/v1/fields/field-zaf-bothaville-maize-03/intelligence", headers=headers_adm)
        assert resp_adm.status_code == 200


# ============================================================================
# 3. SUB-SERVICES ENDPOINTS (SATELLITE, SOIL, WEATHER)
# ============================================================================

@pytest.mark.asyncio
async def test_get_field_satellite_endpoint():
    """Validates GET /api/v1/fields/{id}/satellite endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/satellite?days_window=90", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "observations" in data
        assert len(data["observations"]) >= 10
        assert "latest_scene" in data
        assert "raster_overlay" in data
        assert "grid_geojson" in data
        assert "derived_signals" in data
        assert data["derived_signals"]["vegetation_health_class"] in ["poor", "moderate", "good", "excellent"]


@pytest.mark.asyncio
async def test_get_field_satellite_tiles_info_endpoint():
    """Validates GET /api/v1/fields/{id}/satellite/tiles-info endpoint for MapLibre sources."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/satellite/tiles-info", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["field_id"] == "field-ind-vidarbha-cotton-01"
        assert "image_url" in data
        assert len(data["maplibre_coordinates"]) == 4
        assert len(data["legend"]) == 6


@pytest.mark.asyncio
async def test_get_field_soil_endpoint():
    """Validates GET /api/v1/fields/{id}/soil endpoint with Soil Health Score."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/soil", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "depth_0_30cm_weighted" in data
        assert "texture_class" in data
        assert "soil_health" in data

        shs = data["soil_health"]
        assert 0 <= shs["total_score"] <= 100
        assert shs["health_class"] in ["Excellent", "Good", "Moderate", "Degraded"]
        assert len(shs["limiting_factors"]) <= 3
        assert len(shs["quick_improvement_hints"]) <= 3


@pytest.mark.asyncio
async def test_get_field_weather_endpoint():
    """Validates GET /api/v1/fields/{id}/weather endpoint with derived indicators."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/fields/field-ind-vidarbha-cotton-01/weather", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "daily_forecast_7d" in data
        assert len(data["daily_forecast_7d"]) == 7
        assert "hourly_forecast_48h" in data
        assert "derived_indicators" in data

        indicators = data["derived_indicators"]
        assert "rainfall_anomaly_pct" in indicators
        assert "heat_stress_days" in indicators
        assert "frost_risk_level" in indicators
        assert "drought_class" in indicators
        assert "disease_spread_weather_risk" in indicators
        assert "irrigation_need_mm" in indicators


# ============================================================================
# 4. ASYNCHRONOUS REFRESH & PUBLIC CONFIG ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_trigger_intelligence_refresh_endpoint():
    """Validates POST /api/v1/fields/{id}/intelligence/refresh returns HTTP 202 Accepted."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post("/api/v1/fields/field-ind-vidarbha-cotton-01/intelligence/refresh", headers=headers)

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert "task_id" in data
        assert data["field_id"] == "field-ind-vidarbha-cotton-01"


@pytest.mark.asyncio
async def test_public_crop_thresholds_endpoint():
    """Validates GET /api/v1/intelligence/crop-thresholds is publicly accessible without token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/intelligence/crop-thresholds")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_crops"] >= 8
        assert "cotton" in data["crops"]
        assert "soybean" in data["crops"]
        assert "maize" in data["crops"]
        assert data["crops"]["cotton"]["heat_stress_threshold_celsius"] == 38.0


@pytest.mark.asyncio
async def test_external_providers_health_endpoint():
    """Validates GET /health/providers returns status of all 4 environmental providers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/providers")

        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        providers = data["providers"]
        assert "sentinel2" in providers
        assert "soilgrids" in providers
        assert "open_meteo" in providers
        assert "nasa_power" in providers
        assert providers["sentinel2"]["status"] in ["up", "demo", "degraded"]
