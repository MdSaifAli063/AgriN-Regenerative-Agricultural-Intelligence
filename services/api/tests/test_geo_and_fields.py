import os
import sys
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.main import app
from app.core.exceptions import InvalidGeometryException
from app.core.security import create_dev_token
from app.services.geo_service import GeoService


def test_valid_polygon_metrics_computation():
    """Validates that a valid GeoJSON polygon produces correct lat, lon and area in hectares."""
    valid_polygon = {
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
    }
    lat, lon, area_ha = GeoService.validate_and_compute_metrics(valid_polygon)
    assert 20.581 <= lat <= 20.584
    assert 77.073 <= lon <= 77.078
    assert 0.5 < area_ha < 15.0



def test_non_polygon_geometry_rejected():
    """Validates that Point geometry is rejected with InvalidGeometryException."""
    invalid_point = {
        "type": "Point",
        "coordinates": [77.0735, 20.5810],
    }
    with pytest.raises(InvalidGeometryException) as exc_info:
        GeoService.validate_and_compute_metrics(invalid_point)
    assert "Expected Polygon" in str(exc_info.value)


def test_out_of_bounds_coordinates_rejected():
    """Validates that coordinates outside WGS84 bounds are rejected."""
    out_of_bounds = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.0, 95.0],
                [77.1, 95.0],
                [77.1, 95.1],
                [77.0, 95.1],
                [77.0, 95.0],
            ]
        ],
    }
    with pytest.raises(InvalidGeometryException) as exc_info:
        GeoService.validate_and_compute_metrics(out_of_bounds)
    assert "out of valid WGS84" in str(exc_info.value)


def test_sub_threshold_area_rejected():
    """Validates that microscopic parcels (<0.005 ha) are rejected."""
    tiny_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.00000, 20.00000],
                [77.00001, 20.00000],
                [77.00001, 20.00001],
                [77.00000, 20.00001],
                [77.00000, 20.00000],
            ]
        ],
    }
    with pytest.raises(InvalidGeometryException) as exc_info:
        GeoService.validate_and_compute_metrics(tiny_polygon)
    assert "below minimum threshold" in str(exc_info.value)


def test_create_square_polygon_generator():
    """Validates the square parcel generation helper."""
    square = GeoService.create_square_polygon(lat=20.5824, lon=77.0752, side_meters=200.0)
    assert square["type"] == "Polygon"
    coords = square["coordinates"][0]
    assert len(coords) == 5
    assert coords[0] == coords[-1]  # Closed polygon ring


@pytest.mark.asyncio
async def test_create_field_square_from_point_endpoint():
    """Validates POST /api/v1/fields/from-point generating a field from a center GPS coordinate."""
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
            "field_name": "Generated Pivot Center",
            "latitude": 20.5830,
            "longitude": 77.0760,
            "side_length_meters": 150.0,
            "irrigation_type": "drip",
            "current_crop": "pigeonpea",
        }
        resp = await client.post(
            "/api/v1/fields/from-point?farm_id=farm-ind-vidarbha-01",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["field_name"] == "Generated Pivot Center"
        assert data["area_hectares"] > 0
        assert data["boundary_geojson"]["type"] == "Polygon"
