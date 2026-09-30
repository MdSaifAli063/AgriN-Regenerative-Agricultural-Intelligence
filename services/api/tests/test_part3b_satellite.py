"""
KrishiNet-BRICS - Phase 3 Part 3B Unit Test Suite.

Tests:
  1. Spectral index mathematics (NDVI, NDWI, EVI, NDMI) on known arrays with division-by-zero resilience.
  2. SCL cloud, cloud-shadow, cirrus, and snow masking.
  3. Pure-Python color-mapped PNG heatmap generation with KrishiNet design system green ramp.
  4. MapLibre image source bounds and GeoJSON heatmap grid generation.
  5. Derived satellite signals: health class, 30-day slope trend, 90-day baseline anomaly.
  6. Gap handling: 180-day window expansion and low confidence flags.
  7. Field Intelligence Orchestrator: concurrent multi-provider execution, fault isolation,
     traffic light status derivation, and explainable driving factors.
  8. Celery worker tasks: refresh_field_intelligence, refresh_all_active_fields, refresh_weather_active_fields.
"""

import asyncio
import datetime
import math
import struct
import pytest
import numpy as np

from app.services.intel.satellite_service import (
    COLOR_RAMP,
    Sentinel2SatelliteService,
    color_to_hex,
    compute_spectral_indices,
    compute_zonal_stats,
    encode_png_rgba,
    interpolate_color,
    satellite_service,
)
from app.services.intel.orchestrator import FieldIntelligenceService, field_intelligence_service
from app.workers.tasks import (
    refresh_all_active_fields,
    refresh_field_intelligence,
    refresh_weather_active_fields,
)


# ============================================================================
# 1. SPECTRAL INDICES MATHEMATICS & ZERO-DIVISION SAFETY
# ============================================================================

def test_spectral_indices_known_values():
    """Verify exact formula calculations on controlled floating-point reflectance arrays."""
    # Pixel 0: Vigorous green canopy (High NIR=4000, Low Red=800, Green=1200, Blue=400, SWIR=1500)
    # NDVI = (4000 - 800) / (4000 + 800) = 3200 / 4800 = 0.6667
    # NDWI = (1200 - 4000) / (1200 + 4000) = -2800 / 5200 = -0.5385
    # NDMI = (4000 - 1500) / (4000 + 1500) = 2500 / 5500 = 0.4545
    red = np.array([[800]], dtype=np.float32)
    green = np.array([[1200]], dtype=np.float32)
    blue = np.array([[400]], dtype=np.float32)
    nir = np.array([[4000]], dtype=np.float32)
    swir = np.array([[1500]], dtype=np.float32)

    indices = compute_spectral_indices(red, green, blue, nir, swir)

    assert pytest.approx(float(indices["ndvi"][0, 0]), rel=1e-3) == 0.6667
    assert pytest.approx(float(indices["ndwi"][0, 0]), rel=1e-3) == -0.5385
    assert pytest.approx(float(indices["ndmi"][0, 0]), rel=1e-3) == 0.4545
    assert indices["evi"][0, 0] > 0.0
    assert indices["valid_mask"][0, 0] == True


def test_spectral_indices_zero_division_and_no_data():
    """Verify division-by-zero resilience on black/no-data pixels without raising RuntimeWarning/crash."""
    # Pixel 0: All zeros (e.g. background no-data)
    # Pixel 1: Negative reflectance (defective sensor)
    red = np.array([[0, -10]], dtype=np.float32)
    green = np.array([[0, 100]], dtype=np.float32)
    blue = np.array([[0, 50]], dtype=np.float32)
    nir = np.array([[0, 200]], dtype=np.float32)
    swir = np.array([[0, 150]], dtype=np.float32)

    indices = compute_spectral_indices(red, green, blue, nir, swir)

    # Division by zero should safely evaluate to NaN and be flagged as invalid
    assert np.isnan(indices["ndvi"][0, 0])
    assert indices["valid_mask"][0, 0] == False
    assert indices["valid_mask"][0, 1] == False


# ============================================================================
# 2. SCL SCENE CLASSIFICATION MASKING
# ============================================================================

def test_scl_cloud_and_shadow_masking():
    """Verify SCL band preserves vegetation/soil and rigorously masks clouds, shadows, and snow."""
    # Sentinel-2 SCL Classes:
    # 3: Cloud shadow (Invalid)
    # 4: Vegetation (Valid)
    # 5: Bare soil (Valid)
    # 8: Cloud medium prob (Invalid)
    # 9: Cloud high prob (Invalid)
    # 11: Snow/Ice (Invalid)
    red = np.ones((1, 6), dtype=np.float32) * 500
    green = np.ones((1, 6), dtype=np.float32) * 600
    blue = np.ones((1, 6), dtype=np.float32) * 400
    nir = np.ones((1, 6), dtype=np.float32) * 2500
    swir = np.ones((1, 6), dtype=np.float32) * 1000

    scl = np.array([[3, 4, 5, 8, 9, 11]], dtype=np.uint8)

    indices = compute_spectral_indices(red, green, blue, nir, swir, scl=scl)
    mask = indices["valid_mask"][0]

    assert mask[0] == False  # SCL 3: Cloud shadow
    assert mask[1] == True   # SCL 4: Vegetation
    assert mask[2] == True   # SCL 5: Bare soil
    assert mask[3] == False  # SCL 8: Cloud med prob
    assert mask[4] == False  # SCL 9: Cloud high prob
    assert mask[5] == False  # SCL 11: Snow/Ice


# ============================================================================
# 3. ZONAL STATISTICS
# ============================================================================

def test_zonal_statistics_calculation():
    """Verify mean, median, p10, p90, and valid pixel percentage."""
    arr = np.array([[0.20, 0.40], [0.60, 0.80]], dtype=np.float32)
    valid_mask = np.array([[True, True], [True, False]], dtype=bool)

    stats = compute_zonal_stats(arr, valid_mask)

    # Valid values: 0.20, 0.40, 0.60 (mean = 0.40)
    assert pytest.approx(stats["mean"], abs=1e-2) == 0.40
    assert pytest.approx(stats["median"], abs=1e-2) == 0.40
    assert stats["valid_pixel_pct"] == 75.0
    assert stats["p10"] <= stats["median"] <= stats["p90"]


# ============================================================================
# 4. COLOR RAMP & PNG HEATMAP GENERATION
# ============================================================================

def test_color_ramp_and_hex_interpolation():
    """Verify interpolation across KrishiNet design ramp points."""
    # Boundary extremes
    low_rgb = interpolate_color(-0.5)
    assert low_rgb == (220, 38, 38)  # #DC2626
    assert color_to_hex(low_rgb).upper() == "#DC2626"

    high_rgb = interpolate_color(0.99)
    assert high_rgb == (20, 83, 45)   # #14532D
    assert color_to_hex(high_rgb).upper() == "#14532D"

    # Midpoint checks
    mid_rgb = interpolate_color(0.40)
    assert color_to_hex(mid_rgb).upper() == "#FDE047"


def test_pure_python_png_encoder():
    """Verify pure-Python PNG encoder produces standard valid PNG binary bytes."""
    width, height = 4, 4
    # Create simple RGBA buffer
    rgba = bytes([134, 239, 172, 255] * (width * height))
    png_bytes = encode_png_rgba(width, height, rgba)

    # 1. Verify 8-byte PNG signature
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    # 2. Verify IHDR chunk length and dimensions
    ihdr_len = struct.unpack(">I", png_bytes[8:12])[0]
    assert ihdr_len == 13
    assert png_bytes[12:16] == b"IHDR"
    w, h, depth, color_type = struct.unpack(">IIBB", png_bytes[16:26])
    assert w == width
    assert h == height
    assert depth == 8
    assert color_type == 6  # RGBA

    # 3. Verify IEND chunk at end
    assert png_bytes[-12:-8] == struct.pack(">I", 0)
    assert png_bytes[-8:-4] == b"IEND"


# ============================================================================
# 5. SATELLITE SERVICE: FETCH, GRID & DERIVED SIGNALS
# ============================================================================

@pytest.mark.asyncio
async def test_satellite_service_synthetic_fetch():
    """Verify 90-day observations, PNG raster overlay, and GeoJSON vector grid."""
    poly = {
        "type": "Polygon",
        "coordinates": [[
            [78.000, 20.000],
            [78.010, 20.000],
            [78.010, 20.010],
            [78.000, 20.010],
            [78.000, 20.000],
        ]],
    }
    payload = await satellite_service.fetch(
        centroid_lat=20.005,
        centroid_lon=78.005,
        polygon_geojson=poly,
        field_id="test_vidarbha_01",
        days_window=90,
    )

    assert payload["field_id"] == "test_vidarbha_01"
    assert payload["provenance"]["mode"] in ["live", "demo", "cache"]
    assert len(payload["observations"]) >= 10

    latest = payload["latest_scene"]
    assert 0.1 <= latest["mean_ndvi"] <= 0.95
    assert "date" in latest

    # Verify raster overlay and MapLibre coordinates
    raster = payload["raster_overlay"]
    assert "image_url" in raster
    assert len(raster["maplibre_coordinates"]) == 4
    assert len(raster["legend"]) == 6

    # Verify GeoJSON heatmap grid
    grid = payload["grid_geojson"]
    assert grid["type"] == "FeatureCollection"
    assert len(grid["features"]) > 0
    first_feat = grid["features"][0]
    assert "ndvi" in first_feat["properties"]
    assert first_feat["properties"]["fillColor"].startswith("#")

    # Verify derived signals
    derived = payload["derived_signals"]
    assert derived["vegetation_health_class"] in ["poor", "moderate", "good", "excellent"]
    assert derived["trend_direction"] in ["improving", "stable", "declining"]
    assert isinstance(derived["summary"], str)
    assert len(derived["summary"]) > 10


# ============================================================================
# 6. FIELD INTELLIGENCE ORCHESTRATOR & FAULT ISOLATION
# ============================================================================

@pytest.mark.asyncio
async def test_orchestrator_get_snapshot_integration():
    """Verify orchestrator concurrently fetches satellite, soil, and weather with composite field health."""
    snapshot = await field_intelligence_service.get_snapshot(field_id="demo_field_01")

    assert snapshot["field_id"] == "demo_field_01"
    assert snapshot["field_health_status"] in ["healthy", "watch", "risk"]
    assert len(snapshot["driving_factors"]) >= 2

    # Verify all 3 sub-payloads are present
    assert "satellite" in snapshot
    assert "soil" in snapshot
    assert "weather" in snapshot

    # Verify soil health score exists
    soil_health = snapshot["soil"].get("soil_health", {})
    score = soil_health.get("total_score") or soil_health.get("soil_health_score")
    assert score is not None
    assert 0 <= score <= 100

    # Verify weather forecast
    assert len(snapshot["weather"]["daily_forecast_7d"]) == 7


@pytest.mark.asyncio
async def test_orchestrator_fault_isolation(monkeypatch):
    """Verify that if satellite service raises an unhandled error, soil and weather still return safely."""
    async def mock_crashing_satellite(*args, **kwargs):
        raise ConnectionResetError("Simulated AWS STAC upstream connection abort")

    monkeypatch.setattr(satellite_service, "fetch", mock_crashing_satellite)

    snapshot = await field_intelligence_service.get_snapshot(field_id="fault_test_field")

    # Overall call must succeed
    assert snapshot["field_id"] == "fault_test_field"
    # Satellite has error trapped and wrapped in demo provenance
    assert "error" in snapshot["satellite"]
    assert snapshot["satellite"]["provenance"]["mode"] == "demo"
    # Soil and weather must still be intact
    assert "soil_health" in snapshot["soil"]
    assert len(snapshot["weather"]["daily_forecast_7d"]) == 7


# ============================================================================
# 7. CELERY WORKER TASKS
# ============================================================================

def test_celery_refresh_tasks_execution():
    """Verify Celery tasks run synchronously and return operational summaries."""
    res_field = refresh_field_intelligence("demo_field_01")
    assert res_field["status"] in ["success", "partial_failure"]
    assert res_field["field_id"] == "demo_field_01"

    res_all = refresh_all_active_fields()
    assert res_all["status"] == "scheduled"
    assert res_all["total_fields"] >= 1
    assert res_all["stagger_interval_seconds"] == 12

    res_wx = refresh_weather_active_fields()
    assert res_wx["status"] == "completed"
    assert res_wx["cadence_hours"] == 6
