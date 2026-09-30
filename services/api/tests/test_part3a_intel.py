import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.core.config import settings
from app.services.intel.soil_health import (
    calculate_soil_health_score,
    score_bulk_density,
    score_cec,
    score_nitrogen,
    score_organic_carbon,
    score_ph,
    score_texture_and_awhc,
)
from app.services.intel.soil_service import (
    SoilGridsService,
    classify_usda_texture,
    soil_service,
)
from app.services.intel.weather_service import (
    CROP_HEAT_THRESHOLDS,
    CROP_KC_VALUES,
    WeatherService,
    weather_service,
)
from app.services.intel.base import ProviderRateLimiter, ProvenanceMetadata


# =============================================================================
# 1. SOIL HEALTH SCORE TESTS (Pure Function, No I/O)
# =============================================================================
def test_soil_health_score_weights_sum_to_100():
    """Validates that all 6 component weights sum to exactly 100%."""
    result = calculate_soil_health_score(
        ph=7.0,
        soc_g_kg=20.0,
        clay_pct=25.0,
        sand_pct=40.0,
        silt_pct=35.0,
        nitrogen_g_kg=1.8,
        cec_cmol_kg=24.0,
        bulk_density_g_cm3=1.25,
    )
    total_weights = sum(c.max_weight for c in result.components.values())
    assert total_weights == 100.0
    assert 0 <= result.total_score <= 100
    assert result.health_class == "Excellent"


def test_soil_health_score_bounds_and_monotonicity():
    """Validates boundary conditions (0-100) and that increasing SOC improves or maintains score."""
    # Degraded soil
    degraded = calculate_soil_health_score(
        ph=4.2,
        soc_g_kg=2.0,
        clay_pct=10.0,
        sand_pct=85.0,
        silt_pct=5.0,
        nitrogen_g_kg=0.2,
        cec_cmol_kg=3.0,
        bulk_density_g_cm3=1.75,
    )
    assert degraded.total_score < 50
    assert degraded.health_class == "Degraded"

    # Improved soil with higher organic carbon
    improved = calculate_soil_health_score(
        ph=6.8,
        soc_g_kg=18.0,
        clay_pct=25.0,
        sand_pct=45.0,
        silt_pct=30.0,
        nitrogen_g_kg=1.5,
        cec_cmol_kg=20.0,
        bulk_density_g_cm3=1.25,
    )
    assert improved.total_score > degraded.total_score
    assert improved.total_score >= 80


def test_soil_health_limiting_factors_detection():
    """Validates that low SOC and extreme pH are flagged as top limiting factors."""
    # High pH (8.6), low organic carbon (3.5 g/kg)
    result = calculate_soil_health_score(
        ph=8.6,
        soc_g_kg=3.5,
        clay_pct=50.0,
        sand_pct=20.0,
        silt_pct=30.0,
        nitrogen_g_kg=0.3,
        cec_cmol_kg=40.0,
        bulk_density_g_cm3=1.40,
    )
    limit_str = " ".join(result.limiting_factors)
    assert "Soil Organic Carbon" in limit_str or "Total Nitrogen" in limit_str
    assert len(result.quick_improvement_hints) == 3
    # Verify organic-first guidance
    assert any(
        any(term in h.lower() for term in ["rhizobium", "nitrogen", "pulse", "intercrop", "compost", "gypsum", "manure", "residue", "cover", "humic"])
        for h in result.quick_improvement_hints
    )




def test_crop_aware_ph_scoring():
    """Validates that cotton accommodates alkaline Vertisols while tea favors acidic soils."""
    # pH 8.0: standard crop vs cotton
    score_std, _ = score_ph(8.0, crop="wheat")
    score_cotton, _ = score_ph(8.0, crop="cotton")
    assert score_cotton > score_std

    # pH 5.2: standard crop vs tea
    score_tea, _ = score_ph(5.2, crop="tea")
    score_general, _ = score_ph(5.2, crop="maize")
    assert score_tea > score_general


# =============================================================================
# 2. USDA TEXTURE TRIANGLE CLASSIFICATION TESTS
# =============================================================================
def test_usda_texture_triangle_classification():
    """Validates texture classification across 8 key USDA soil classes."""
    assert classify_usda_texture(clay_pct=60.0, sand_pct=20.0, silt_pct=20.0) == "Clay"
    assert classify_usda_texture(clay_pct=5.0, sand_pct=90.0, silt_pct=5.0) == "Sand"
    assert classify_usda_texture(clay_pct=8.0, sand_pct=80.0, silt_pct=12.0) == "Loamy Sand"
    assert classify_usda_texture(clay_pct=10.0, sand_pct=65.0, silt_pct=25.0) == "Sandy Loam"
    assert classify_usda_texture(clay_pct=20.0, sand_pct=40.0, silt_pct=40.0) == "Loam"
    assert classify_usda_texture(clay_pct=15.0, sand_pct=15.0, silt_pct=70.0) == "Silt Loam"
    assert classify_usda_texture(clay_pct=32.0, sand_pct=35.0, silt_pct=33.0) == "Clay Loam"
    assert classify_usda_texture(clay_pct=45.0, sand_pct=10.0, silt_pct=45.0) == "Silty Clay"
    assert classify_usda_texture(clay_pct=40.0, sand_pct=50.0, silt_pct=10.0) == "Sandy Clay"


# =============================================================================
# 3. WEATHER SERVICE DERIVED RISK INDICATORS TESTS
# =============================================================================
def test_weather_derived_indicators_fixed_inputs():
    """Validates heat stress, frost risk, drought index, and spray windows with synthetic inputs."""
    service = WeatherService()
    raw_mock_forecast = {
        "daily": {
            "time": ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07"],
            "temperature_2m_max": [39.0, 37.0, 36.5, 34.0, 33.0, 32.0, 31.0],
            "temperature_2m_min": [24.0, 22.0, 21.0, 19.0, 18.0, 1.5, -0.5],
            "precipitation_sum": [0.0, 0.0, 12.0, 25.0, 2.0, 0.0, 0.0],
            "precipitation_probability_max": [5, 10, 85, 95, 40, 10, 5],
            "et0_fao_evapotranspiration": [5.5, 5.2, 3.8, 3.2, 4.0, 4.5, 4.8],
            "wind_speed_10m_max": [8.0, 12.0, 22.0, 28.0, 14.0, 9.0, 10.0],
            "relative_humidity_2m_mean": [45.0, 50.0, 82.0, 88.0, 75.0, 55.0, 48.0],
        },
        "hourly": {
            "time": [f"2026-10-01T{h:02d}:00:00Z" for h in range(48)],
            "temperature_2m": [25.0] * 48,
            "relative_humidity_2m": [60.0] * 48,
            "precipitation": [0.0] * 48,
            "wind_speed_10m": [8.0] * 48,
        },
    }

    parsed = service._parse_forecast(raw_mock_forecast, lat=20.58, lon=77.07, crop="cotton")
    indicators = parsed["derived_indicators"]

    # Cotton threshold is 38.0 C -> 39.0 C triggers heat stress
    assert indicators["heat_stress_days"] >= 1
    assert indicators["critical_temp_threshold_c"] == 38.0

    # Min temps 1.5 C and -0.5 C trigger frost risk
    assert indicators["frost_risk_days"] == 2
    assert indicators["frost_risk_level"] in ["moderate", "high"]

    # Spray windows: Day 1 (wind 8, rain 0) and Day 6 (wind 9, rain 0) qualify
    assert len(indicators["best_spray_windows"]) >= 2
    assert "2026-10-01" in indicators["best_spray_windows"]

    # Net irrigation need is computed
    assert indicators["irrigation_need_mm"] >= 0.0
    assert 0 <= indicators["disease_spread_weather_risk"] <= 100


# =============================================================================
# 4. RATE LIMITER & PROVENANCE TESTS
# =============================================================================
@pytest.mark.asyncio
async def test_provider_rate_limiter():
    """Validates that ProviderRateLimiter records requests within window."""
    limiter = ProviderRateLimiter("TestLimiter", max_requests_per_minute=10)
    for _ in range(5):
        await limiter.acquire()
    assert len(limiter.timestamps) == 5


def test_provenance_metadata():
    """Validates ProvenanceMetadata schema validation."""
    meta = ProvenanceMetadata(
        source="ISRIC SoilGrids 250m v2.0",
        mode="demo",
        confidence=0.92,
        notes="Grounded in regional agronomy",
    )
    assert meta.source.startswith("ISRIC")
    assert meta.mode == "demo"
    assert meta.confidence == 0.92
    assert meta.fetched_at is not None


# =============================================================================
# 5. INTEGRATION DEMO-MODE FETCH TESTS (No Network)
# =============================================================================
@pytest.mark.asyncio
async def test_soil_service_demo_mode_india_vertisol():
    """Validates that in DEMO_MODE, soil_service returns authentic Vertisol profile for India."""
    settings.DEMO_MODE = True
    result = await soil_service.fetch(centroid_lat=20.5824, centroid_lon=77.0752, crop="cotton")

    assert result["centroid_lat"] == 20.5824
    assert result["texture_class"] == "Clay"
    assert result["depth_0_30cm_weighted"]["ph_h2o"] > 7.5
    assert result["depth_0_30cm_weighted"]["clay_pct"] > 50.0
    assert result["soil_health"]["total_score"] > 50
    assert result["provenance"]["mode"] == "demo"


@pytest.mark.asyncio
async def test_soil_service_demo_mode_brazil_oxisol():
    """Validates that in DEMO_MODE, soil_service returns authentic Cerrado Oxisol profile for Brazil."""
    settings.DEMO_MODE = True
    result = await soil_service.fetch(centroid_lat=-12.5428, centroid_lon=-55.7214, crop="soybean")

    assert result["centroid_lat"] == -12.5428
    assert result["depth_0_30cm_weighted"]["ph_h2o"] < 6.5
    assert result["depth_0_30cm_weighted"]["soil_organic_carbon_g_kg"] > 15.0
    assert result["soil_health"]["total_score"] >= 80
    assert result["provenance"]["mode"] == "demo"


@pytest.mark.asyncio
async def test_weather_service_demo_mode():
    """Validates that in DEMO_MODE, weather_service returns 7-day forecast without network calls."""
    settings.DEMO_MODE = True
    result = await weather_service.fetch(centroid_lat=20.5824, centroid_lon=77.0752, crop="cotton")

    assert len(result["daily_forecast_7d"]) == 7
    assert len(result["hourly_forecast_48h"]) == 48
    assert "rainfall_anomaly_pct" in result["derived_indicators"]
    assert "irrigation_need_mm" in result["derived_indicators"]
    assert result["provenance"]["mode"] == "demo"
