"""
KrishiNet-BRICS - Phase 4 Part 4D AI Advisory Endpoints Test Suite.

Validates:
  1. POST /api/v1/fields/{field_id}/advisory (Generates valid AdvisoryContract)
  2. GET /api/v1/fields/{field_id}/advisories (Lists chronological advisory history)
  3. GET /api/v1/advisories/{advisory_id} (Retrieves stored AdvisoryContract)
  4. GET /api/v1/advisories/{advisory_id}/explainability (Dual presentation: farmer vs officer)
  5. GET /api/v1/advisories/{advisory_id}/trace (Granular execution & safety trace)
  6. GET /api/v1/advisories/{advisory_id}/actions (Lists 30-day action tasks)
  7. POST /api/v1/advisories/{advisory_id}/actions/{action_id}/complete (Calendar task toggle)
  8. POST /api/v1/advisories/{advisory_id}/feedback (Adoption rating & practices)
  9. POST /api/v1/advisories/{advisory_id}/translate (Dynamic BRICS multilingual translation)
 10. GET /api/v1/ai/health (AI engine health check probe)
 11. Error handling (404 for unknown field, 404 for unknown advisory, 404 for unknown action)
"""

import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.security import create_dev_token


# ============================================================================
# 1. GENERATE ADVISORY ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_generate_field_advisory_endpoint():
    """Validates generating a structured AdvisoryContract via POST /fields/{id}/advisory."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "language": "en",
            "farmer_notes": "Planning next rotation cycle, soil feels dry.",
            "preferred_crop": "cotton",
            "force_refresh": True,
        }

        resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json=payload,
            headers=headers,
        )

        assert resp.status_code == 201
        data = resp.json()

        # Contract schema validation
        assert "meta" in data
        assert "field_summary" in data
        assert "crop_recommendations" in data
        assert "regenerative_practices" in data
        assert "sowing_window" in data
        assert "irrigation_schedule" in data
        assert "fertiliser_plan" in data
        assert "action_calendar_30d" in data
        assert "what_to_do_today" in data
        assert "risks_and_warnings" in data
        assert "explainability" in data
        assert "confidence" in data

        assert data["meta"]["field_id"] == "field-ind-vidarbha-cotton-01"
        assert len(data["crop_recommendations"]) >= 1
        assert data["confidence"]["overall"] >= 0.50
        assert data["confidence"]["level"].lower() in ["high", "medium", "low"]


@pytest.mark.asyncio
async def test_generate_advisory_nonexistent_field_returns_404():
    """Validates 404 when generating advisory for a missing field."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/v1/fields/nonexistent-field-id/advisory",
            json={"language": "en"},
            headers=headers,
        )
        assert resp.status_code == 404
        err = resp.json().get("error", {}).get("message", "") or resp.json().get("detail", "")
        assert "not found" in err.lower()


# ============================================================================
# 2. ADVISORY LISTING & GET BY ID
# ============================================================================

@pytest.mark.asyncio
async def test_list_and_get_field_advisories():
    """Validates listing advisory history and fetching by advisory ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Generate an advisory first
        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en", "preferred_crop": "cotton"},
            headers=headers,
        )
        assert gen_resp.status_code == 201
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        # 2. List advisories for the field
        list_resp = await client.get(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisories?limit=5",
            headers=headers,
        )
        assert list_resp.status_code == 200
        history = list_resp.json()
        assert isinstance(history, list)
        assert len(history) >= 1
        ids = [h["advisory_id"] for h in history]
        assert advisory_id in ids

        # 3. Retrieve full contract by advisory_id
        get_resp = await client.get(f"/api/v1/advisories/{advisory_id}", headers=headers)
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["meta"]["advisory_id"] == advisory_id
        assert fetched["meta"]["field_id"] == "field-ind-vidarbha-cotton-01"


@pytest.mark.asyncio
async def test_get_advisory_not_found_returns_404():
    """Validates 404 for unknown advisory ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/advisories/unknown-advisory-999")
        assert resp.status_code == 404
        err = resp.json().get("error", {}).get("message", "") or resp.json().get("detail", "")
        assert "not found" in err.lower()


# ============================================================================
# 3. EXPLAINABILITY & TRACE ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_advisory_explainability_dual_presentation():
    """Validates farmer visual trust brief vs extension officer diagnostic view."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-officer-ind-004", "role": "extension_officer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        # Generate advisory
        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en", "preferred_crop": "pigeonpea"},
            headers=headers,
        )
        assert gen_resp.status_code == 201
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        # View 1: Farmer default view
        farmer_resp = await client.get(
            f"/api/v1/advisories/{advisory_id}/explainability?for_officer=false",
            headers=headers,
        )
        assert farmer_resp.status_code == 200
        farmer_view = farmer_resp.json()
        assert farmer_view["view"] == "farmer_plain_language"
        assert "headline_reason" in farmer_view
        assert len(farmer_view["key_factors"]) >= 1
        assert "trust_badge" in farmer_view

        # View 2: Extension Officer deep diagnostic view
        officer_resp = await client.get(
            f"/api/v1/advisories/{advisory_id}/explainability?for_officer=true",
            headers=headers,
        )
        assert officer_resp.status_code == 200
        officer_view = officer_resp.json()
        assert officer_view["view"] == "extension_officer_diagnostic"
        assert "signals_used" in officer_view
        assert "counterfactual_analysis" in officer_view
        assert "confidence_breakdown" in officer_view


@pytest.mark.asyncio
async def test_advisory_execution_trace_endpoint():
    """Validates inspection of execution trace, timings, and rules baseline."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-admin-001", "role": "government_admin", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        trace_resp = await client.get(f"/api/v1/advisories/{advisory_id}/trace", headers=headers)
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()

        assert trace_data["advisory_id"] == advisory_id
        assert trace_data["field_id"] == "field-ind-vidarbha-cotton-01"
        assert "confidence_score" in trace_data
        assert "trace" in trace_data


# ============================================================================
# 4. ACTION CALENDAR ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_action_calendar_listing_and_completion_toggle():
    """Validates listing tasks and toggling completion status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        # Generate advisory with action plan
        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        adv_payload = gen_resp.json()
        advisory_id = adv_payload["meta"]["advisory_id"]

        # List actions from endpoint
        actions_resp = await client.get(f"/api/v1/advisories/{advisory_id}/actions", headers=headers)
        assert actions_resp.status_code == 200
        actions = actions_resp.json()
        assert len(actions) >= 1
        action_id = actions[0]["action_id"]

        # Toggle completion ON
        toggle_resp = await client.post(
            f"/api/v1/advisories/{advisory_id}/actions/{action_id}/complete",
            headers=headers,
        )
        assert toggle_resp.status_code == 200
        t1 = toggle_resp.json()
        assert t1["status"] == "success"
        assert t1["is_completed"] is True
        assert t1["completed_at"] is not None

        # Toggle completion OFF
        toggle_resp2 = await client.post(
            f"/api/v1/advisories/{advisory_id}/actions/{action_id}/complete",
            headers=headers,
        )
        assert toggle_resp2.status_code == 200
        t2 = toggle_resp2.json()
        assert t2["status"] == "success"
        assert t2["is_completed"] is False
        assert t2["completed_at"] is None


@pytest.mark.asyncio
async def test_complete_action_item_not_found_returns_404():
    """Validates 404 when toggling a nonexistent action item."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        resp = await client.post(
            f"/api/v1/advisories/{advisory_id}/actions/nonexistent-action-999/complete",
            headers=headers,
        )
        assert resp.status_code == 404
        err = resp.json().get("error", {}).get("message", "") or resp.json().get("detail", "")
        assert "not found" in err.lower()


# ============================================================================
# 5. FEEDBACK SUBMISSION
# ============================================================================

@pytest.mark.asyncio
async def test_submit_advisory_feedback():
    """Validates farmer/extension officer feedback submission with star rating."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        feedback_payload = {
            "rating": 5,
            "comment": "Mulching recommendations preserved significant soil moisture during the dry spell.",
            "practices_adopted": ["mulching", "intercropping_legumes"],
        }
        fb_resp = await client.post(
            f"/api/v1/advisories/{advisory_id}/feedback",
            json=feedback_payload,
            headers=headers,
        )
        assert fb_resp.status_code == 200
        fb_data = fb_resp.json()
        assert fb_data["status"] == "recorded"
        assert fb_data["rating"] == 5
        assert fb_data["advisory_id"] == advisory_id


@pytest.mark.asyncio
async def test_feedback_invalid_rating_rejected():
    """Validates that ratings outside 1-5 return 422 Unprocessable Content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        resp = await client.post(
            f"/api/v1/advisories/{advisory_id}/feedback",
            json={"rating": 10},
            headers=headers,
        )
        assert resp.status_code == 422


# ============================================================================
# 6. DYNAMIC MULTILINGUAL TRANSLATION ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_translate_advisory_endpoint():
    """Validates dynamically translating an advisory into Hindi or Portuguese."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({"sub": "user-farmer-ind-001", "role": "farmer", "country": "IND"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Generate in English
        gen_resp = await client.post(
            "/api/v1/fields/field-ind-vidarbha-cotton-01/advisory",
            json={"language": "en"},
            headers=headers,
        )
        advisory_id = gen_resp.json()["meta"]["advisory_id"]

        # 2. Translate to Hindi
        trans_resp = await client.post(
            f"/api/v1/advisories/{advisory_id}/translate",
            json={"target_language": "hi"},
            headers=headers,
        )
        assert trans_resp.status_code == 200
        trans_contract = trans_resp.json()

        assert trans_contract["meta"]["language"] == "hi"
        assert trans_contract["meta"]["advisory_id"] == advisory_id
        # Invariant preservation
        assert trans_contract["confidence"]["overall"] == gen_resp.json()["confidence"]["overall"]
        assert len(trans_contract["crop_recommendations"]) == len(gen_resp.json()["crop_recommendations"])


# ============================================================================
# 7. AI ENGINE HEALTH PROBE
# ============================================================================

@pytest.mark.asyncio
async def test_ai_engine_health_endpoint():
    """Validates GET /api/v1/ai/health probe status, token budget, and agronomic catalog."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ai/health")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "healthy"
        assert "node_id" in data
        assert "node_country" in data
        assert "gemini_model" in data
        assert "knowledge_base" in data
        assert data["knowledge_base"]["indexed_documents"] >= 0
        assert len(data["supported_crops"]) >= 8
        assert "cotton" in data["supported_crops"]
        assert "soybean" in data["supported_crops"]
        assert "maize" in data["supported_crops"]
        assert "hi" in data["supported_languages"]
        assert "pt" in data["supported_languages"]
        assert "ru" in data["supported_languages"]
        assert "zh" in data["supported_languages"]
