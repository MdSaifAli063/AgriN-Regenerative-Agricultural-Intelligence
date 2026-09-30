import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.config import settings
from app.core.security import create_dev_token


@pytest.fixture(autouse=True)
def ensure_demo_mode():
    orig = settings.DEMO_MODE
    settings.DEMO_MODE = True
    yield
    settings.DEMO_MODE = orig



@pytest.mark.asyncio
async def test_liveness_probe_returns_200_alive():
    """Validates that GET /health/live returns HTTP 200 with status 'alive'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_structure():
    """Validates that GET /health/ready evaluates core infrastructure components."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/ready")
        assert resp.status_code in [200, 503]
        data = resp.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "redis" in data["components"]
        assert "minio" in data["components"]


@pytest.mark.asyncio
async def test_demo_mode_status_reporting():
    """Validates that GET /health/demo-mode reports demo fallbacks and node identity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/demo-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert "demo_mode" in data
        assert "node_id" in data
        assert "node_country" in data
        assert "fallback_providers" in data


@pytest.mark.asyncio
async def test_background_task_status_endpoint():
    """Validates that GET /api/v1/tasks/{task_id} returns task status safely."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_dev_token({
            "sub": "user-farmer-ind-001",
            "role": "farmer",
            "country": "IND",
            "name": "Ramesh Patil",
        })
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/v1/tasks/task-sat-fetch-mock-001", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-sat-fetch-mock-001"
        assert "status" in data
