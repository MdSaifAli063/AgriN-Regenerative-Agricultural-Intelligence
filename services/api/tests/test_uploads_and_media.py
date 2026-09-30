import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app


@pytest.mark.asyncio
async def test_presign_jpeg_upload():
    """Validates presigned upload URL generation for standard JPEG leaf image."""
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
        assert data["expires_in_seconds"] == 900


@pytest.mark.asyncio
async def test_presign_png_upload():
    """Validates presigned upload URL generation for PNG image."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "image/png", "file_size_bytes": 1024 * 1024},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["object_key"].startswith("uploads/")


@pytest.mark.asyncio
async def test_presign_webp_upload():
    """Validates presigned upload URL generation for WebP image."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "image/webp", "file_size_bytes": 2 * 1024 * 1024},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["object_key"].startswith("uploads/")


@pytest.mark.asyncio
async def test_presign_disallowed_mime_rejected():
    """Validates that non-image MIME types (e.g. application/pdf) are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "application/pdf", "file_size_bytes": 1024},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_presign_oversized_file_rejected():
    """Validates that files exceeding 10MB ceiling are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "image/jpeg", "file_size_bytes": 15 * 1024 * 1024},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_presign_zero_byte_file_rejected():
    """Validates that empty 0-byte upload requests are rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/uploads/presign",
            json={"content_type": "image/jpeg", "file_size_bytes": 0},
        )
        assert resp.status_code == 422
