"""
KrishiNet-BRICS - Deterministic Demo Fixture Generator.

Generates realistic hand-crafted and synthetic fixtures for the 3 demo farms:
  1. India (Maharashtra - Vidarbha):
     - Crop: Cotton
     - Soil: Vertisol (Black Cotton Soil, alkaline pH 7.8, high clay 48%, low SOC 0.52%)
     - Climate: Semi-arid monsoon, 37°C heat stress days
  2. Brazil (Mato Grosso - Sorriso):
     - Crop: Soybean
     - Soil: Cerrado Oxisol / Latosol (Acidic pH 5.4, high SOC 2.2%, low CEC 7.2)
     - Climate: Tropical humid, high humidity 78%, high Asian soybean rust fungal risk
     - Satellite: Features a visible mid-season stress dip (days 40-65) for anomaly testing
  3. South Africa (Free State - Welkom):
     - Crop: Maize
     - Soil: Arenosol / Loamy Sand (Neutral pH 6.3, low clay 14%, high sand 72%)
     - Climate: Highveld continental, warm days (28°C), cold nights (2°C frost risk), mild drought

Writes output to:
  - data/seed/fixtures/india_vidarbha_cotton.json
  - data/seed/fixtures/india_vidarbha_cotton_ndvi.png
  - data/seed/fixtures/brazil_cerrado_soybean.json
  - data/seed/fixtures/brazil_cerrado_soybean_ndvi.png
  - data/seed/fixtures/south_africa_freestate_maize.json
  - data/seed/fixtures/south_africa_freestate_maize_ndvi.png
"""

import datetime
import json
import math
import os
import struct
import zlib
from typing import Any, Dict, List, Tuple

# KrishiNet Design System Green Ramp
COLOR_RAMP: List[Tuple[float, Tuple[int, int, int]]] = [
    (-0.20, (220, 38, 38)),   # #DC2626 (Red - Bare/Stressed/Water)
    (0.20, (245, 158, 11)),   # #F59E0B (Amber - Sparse vegetation)
    (0.40, (253, 224, 71)),   # #FDE047 (Yellow - Moderate vegetation)
    (0.60, (134, 239, 172)),  # #86EFAC (Light Green - Good vigor)
    (0.75, (22, 163, 74)),    # #16A34A (Green - High vigor)
    (0.90, (20, 83, 45)),     # #14532D (Dark Forest Green - Dense canopy)
]


def interpolate_color(val: float) -> Tuple[int, int, int]:
    if math.isnan(val) or val is None:
        return (0, 0, 0)
    if val <= COLOR_RAMP[0][0]:
        return COLOR_RAMP[0][1]
    if val >= COLOR_RAMP[-1][0]:
        return COLOR_RAMP[-1][1]
    for i in range(len(COLOR_RAMP) - 1):
        v0, c0 = COLOR_RAMP[i]
        v1, c1 = COLOR_RAMP[i + 1]
        if v0 <= val <= v1:
            ratio = (val - v0) / (v1 - v0) if (v1 - v0) > 0 else 0.0
            r = int(c0[0] + ratio * (c1[0] - c0[0]))
            g = int(c0[1] + ratio * (c1[1] - c0[1]))
            b = int(c0[2] + ratio * (c1[2] - c0[2]))
            return (r, g, b)
    return COLOR_RAMP[-1][1]


def color_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def encode_png_rgba(width: int, height: int, rgba_bytes: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    raw_scanlines = bytearray()
    row_bytes = width * 4
    for y in range(height):
        raw_scanlines.append(0)
        start = y * row_bytes
        raw_scanlines.extend(rgba_bytes[start : start + row_bytes])
    idat = chunk(b"IDAT", zlib.compress(bytes(raw_scanlines), level=6))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def generate_heatmap_png(mean_ndvi: float, width: int = 128, height: int = 128) -> bytes:
    rgba = bytearray()
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - width / 2.0) ** 2 + (y - height / 2.0) ** 2) / (width / 1.414)
            val = mean_ndvi + 0.15 * (1.0 - dist) - 0.05 * math.sin(x / 10.0)
            val = max(0.05, min(0.95, val))
            rgb = interpolate_color(val)
            rgba.extend([rgb[0], rgb[1], rgb[2], 240])
    return encode_png_rgba(width, height, bytes(rgba))


def generate_time_series(base_ndvi: float, days: int = 90, has_dip: bool = False) -> List[Dict[str, Any]]:
    today = datetime.date.today()
    obs = []
    for i in range(days, 0, -5):
        dt = today - datetime.timedelta(days=i)
        progress = (days - i) / float(days)
        if has_dip and 40 <= (days - i) <= 65:
            curve = 0.25 - 0.20 * math.sin(math.pi * ((days - i - 40) / 25.0))
        else:
            curve = 0.25 * math.sin(math.pi * progress)
        val = max(0.18, min(0.88, base_ndvi + curve))
        obs.append({
            "scene_id": f"S2A_MSIL2A_{dt.strftime('%Y%m%d')}_DEMO",
            "date": dt.isoformat(),
            "cloud_cover_pct": round(3.5 + 4.0 * math.sin(i), 1),
            "mean_ndvi": round(val, 4),
            "p10_ndvi": round(val - 0.08, 4),
            "p90_ndvi": round(val + 0.07, 4),
            "mean_ndwi": round(-0.35 + 0.08 * curve, 4),
            "mean_evi": round(val * 0.82, 4),
            "mean_ndmi": round(0.10 + 0.12 * curve, 4),
            "valid_pixel_pct": 94.5,
        })
    return obs


def build_farm_fixture(
    farm_id: str,
    field_id: str,
    field_name: str,
    country_iso: str,
    crop: str,
    lat: float,
    lon: float,
    base_ndvi: float,
    has_dip: bool,
    soil_props: Dict[str, Any],
    weather_props: Dict[str, Any],
) -> Tuple[Dict[str, Any], bytes]:
    # 1. Satellite observations
    series = generate_time_series(base_ndvi, days=90, has_dip=has_dip)
    latest_ndvi = series[-1]["mean_ndvi"]
    png_bytes = generate_heatmap_png(latest_ndvi)

    d = 0.003
    boundary = {
        "type": "Polygon",
        "coordinates": [[
            [round(lon - d, 4), round(lat - d, 4)],
            [round(lon + d, 4), round(lat - d, 4)],
            [round(lon + d, 4), round(lat + d, 4)],
            [round(lon - d, 4), round(lat + d, 4)],
            [round(lon - d, 4), round(lat - d, 4)],
        ]],
    }

    trend_dir = "declining" if has_dip else "improving"
    health_class = "good" if latest_ndvi >= 0.50 else "moderate"

    # GeoJSON Grid
    grid_features = []
    cell_idx = 0
    for r in range(4):
        for c in range(4):
            c_val = round(latest_ndvi + (r + c - 3) * 0.02, 3)
            poly = {
                "type": "Polygon",
                "coordinates": [[
                    [round(lon - d + c * (2*d/4), 4), round(lat - d + r * (2*d/4), 4)],
                    [round(lon - d + (c+1) * (2*d/4), 4), round(lat - d + r * (2*d/4), 4)],
                    [round(lon - d + (c+1) * (2*d/4), 4), round(lat - d + (r+1) * (2*d/4), 4)],
                    [round(lon - d + c * (2*d/4), 4), round(lat - d + (r+1) * (2*d/4), 4)],
                    [round(lon - d + c * (2*d/4), 4), round(lat - d + r * (2*d/4), 4)],
                ]],
            }
            grid_features.append({
                "type": "Feature",
                "id": cell_idx,
                "geometry": poly,
                "properties": {
                    "id": cell_idx,
                    "ndvi": c_val,
                    "fillColor": color_to_hex(interpolate_color(c_val)),
                    "opacity": 0.85,
                },
            })
            cell_idx += 1

    satellite_payload = {
        "field_id": field_id,
        "provenance": {
            "source": "Sentinel-2 L2A (Verified Fixture)",
            "mode": "demo",
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ttl_seconds": 86400,
            "confidence": 0.95,
            "notes": "Hand-crafted regional seasonal telemetry baseline.",
        },
        "low_confidence": False,
        "observations_count": len(series),
        "observations": series,
        "latest_scene": series[-1],
        "raster_overlay": {
            "image_url": f"http://localhost:9000/krishinet-assets/fields/{field_id}/satellite/ndvi_heatmap.png?mock_token=presigned_demo",
            "bbox": [round(lon - d, 4), round(lat - d, 4), round(lon + d, 4), round(lat + d, 4)],
            "maplibre_coordinates": [
                [round(lon - d, 4), round(lat + d, 4)],
                [round(lon + d, 4), round(lat + d, 4)],
                [round(lon + d, 4), round(lat - d, 4)],
                [round(lon - d, 4), round(lat - d, 4)],
            ],
            "legend": [
                {"label": "Stressed / Water (< 0.20)", "color": "#DC2626"},
                {"label": "Sparse Vegetation (0.20 - 0.40)", "color": "#F59E0B"},
                {"label": "Moderate Canopy (0.40 - 0.60)", "color": "#FDE047"},
                {"label": "Healthy Biomass (0.60 - 0.75)", "color": "#86EFAC"},
                {"label": "Dense Crop Canopy (0.75 - 0.85)", "color": "#16A34A"},
                {"label": "Peak Photosynthesis (> 0.85)", "color": "#14532D"},
            ],
        },
        "grid_geojson": {
            "type": "FeatureCollection",
            "features": grid_features,
        },
        "derived_signals": {
            "vegetation_health_class": health_class,
            "trend_direction": trend_dir,
            "slope_per_day": -0.0035 if has_dip else 0.0028,
            "baseline_90d_ndvi": round(base_ndvi + 0.12, 3),
            "latest_ndvi": latest_ndvi,
            "anomaly_vs_90d_baseline_pct": -12.4 if has_dip else 4.6,
            "summary": f"Vegetation vigor is {health_class.capitalize()} (NDVI {latest_ndvi:.2f}) with {trend_dir} canopy momentum.",
        },
    }

    # 2. Soil payload
    soil_payload = {
        "centroid_lat": lat,
        "centroid_lon": lon,
        "texture_class": soil_props["texture_class"],
        "depth_0_30cm_weighted": soil_props["weighted"],
        "raw_depth_layers": soil_props["layers"],
        "soil_health": soil_props["soil_health"],
        "provenance": {
            "source": "ISRIC SoilGrids 250m v2.0 (Verified Fixture)",
            "mode": "demo",
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ttl_seconds": 86400 * 30,
            "confidence": 0.92,
            "notes": soil_props["notes"],
        },
    }

    # 3. Weather payload
    today_dt = datetime.date.today()
    daily_fx = []
    for day_i in range(7):
        cur_dt = today_dt + datetime.timedelta(days=day_i)
        t_max = weather_props["t_max"] + math.sin(day_i) * 1.5
        t_min = weather_props["t_min"] + math.cos(day_i) * 1.2
        rain = weather_props["rain_daily"][day_i]
        daily_fx.append({
            "date": cur_dt.isoformat(),
            "temp_max_c": round(t_max, 1),
            "temp_min_c": round(t_min, 1),
            "precipitation_mm": round(rain, 1),
            "precipitation_probability_pct": 80 if rain > 2.0 else 10,
            "et0_fao_evapotranspiration_mm": 4.5,
            "wind_speed_max_kmh": round(12.0 + math.sin(day_i) * 4.0, 1),
            "relative_humidity_mean_pct": weather_props["rh"],
            "heat_stress_flag": t_max > weather_props["heat_thresh"],
            "frost_risk_flag": t_min <= 2.0,
            "is_spray_window": rain < 1.0 and (12.0 + math.sin(day_i) * 4.0) < 15.0,
        })

    weather_payload = {
        "centroid_lat": lat,
        "centroid_lon": lon,
        "current_temp_c": round(weather_props["t_max"] - 4.0, 1),
        "current_humidity_pct": weather_props["rh"],
        "current_conditions": weather_props["conditions"],
        "daily_forecast_7d": daily_fx,
        "hourly_forecast_48h": [
            {
                "timestamp": f"{today_dt.isoformat()}T{h:02d}:00:00Z",
                "temp_c": round(weather_props["t_min"] + 10.0 * math.sin(h / 24.0 * math.pi), 1),
                "relative_humidity_pct": weather_props["rh"],
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 10.0,
            }
            for h in range(48)
        ],
        "derived_indicators": weather_props["derived_indicators"],
        "provenance": {
            "source": "Open-Meteo & NASA POWER (Verified Fixture)",
            "mode": "demo",
            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ttl_seconds": 21600,
            "confidence": 0.94,
            "notes": weather_props["notes"],
        },
    }

    # Consolidated Orchestrator Snapshot
    fixture = {
        "farm_id": farm_id,
        "field_id": field_id,
        "field_name": field_name,
        "country_iso": country_iso,
        "crop": crop,
        "centroid_lat": lat,
        "centroid_lon": lon,
        "boundary_geojson": boundary,
        "refreshed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "field_health_status": weather_props.get("field_health_status", "watch"),
        "driving_factors": weather_props.get("driving_factors", []),
        "satellite": satellite_payload,
        "soil": soil_payload,
        "weather": weather_payload,
    }

    return fixture, png_bytes


def main():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "data", "seed", "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    print("Generating KrishiNet-BRICS Demo Fixtures...")

    # ------------------------------------------------------------------------
    # 1. INDIA (Vidarbha Vertisol Cotton)
    # ------------------------------------------------------------------------
    ind_soil = {
        "texture_class": "Clay",
        "weighted": {
            "ph_h2o": 7.8,
            "soc_g_kg": 5.2,
            "nitrogen_g_kg": 0.52,
            "clay_pct": 48.0,
            "sand_pct": 22.0,
            "silt_pct": 30.0,
            "cec_cmol_kg": 38.5,
            "bulk_density_g_cm3": 1.45,
            "awhc_mm_per_m": 160.0,
        },
        "layers": {
            "phh2o": {"0-5cm": 7.7, "5-15cm": 7.8, "15-30cm": 7.9},
            "soc": {"0-5cm": 6.8, "5-15cm": 5.2, "15-30cm": 4.4},
            "nitrogen": {"0-5cm": 0.65, "5-15cm": 0.52, "15-30cm": 0.44},
            "clay": {"0-5cm": 46.0, "5-15cm": 48.0, "15-30cm": 49.0},
            "sand": {"0-5cm": 24.0, "5-15cm": 22.0, "15-30cm": 21.0},
            "silt": {"0-5cm": 30.0, "5-15cm": 30.0, "15-30cm": 30.0},
            "cec": {"0-5cm": 36.0, "5-15cm": 38.0, "15-30cm": 40.0},
            "bdod": {"0-5cm": 1.40, "5-15cm": 1.45, "15-30cm": 1.48},
        },
        "soil_health": {
            "total_score": 62,
            "health_class": "watch",
            "confidence": 0.92,
            "components": {
                "organic_carbon": {"score": 38.0, "weight": 25.0, "status": "risk"},
                "ph_suitability": {"score": 85.0, "weight": 20.0, "status": "healthy"},
                "nitrogen": {"score": 40.0, "weight": 15.0, "status": "risk"},
                "texture_water": {"score": 88.0, "weight": 15.0, "status": "healthy"},
                "cec": {"score": 95.0, "weight": 15.0, "status": "healthy"},
                "bulk_density": {"score": 60.0, "weight": 10.0, "status": "watch"},
            },
            "limiting_factors": [
                "Low Soil Organic Carbon (0.52% vs target 1.50%)",
                "Total Nitrogen deficit (0.52 g/kg vs target 1.20 g/kg)",
                "Subsurface compaction / high bulk density (1.45 g/cm³)",
            ],
            "plain_language_interpretation": "Heavy Vertisol with outstanding water retention and mineral reserves, but depleted organic carbon and nitrogen.",
            "quick_improvement_hints": [
                "Apply 5 tonnes/ha farmyard manure or vermicompost prior to monsoon sowing",
                "Intercrop with short-duration pigeonpea or green gram (Rhizobium bio-inoculant)",
                "Adopt minimum tillage to prevent deep cracking and soil moisture loss",
            ],
        },
        "notes": "Authentic Vidarbha Deep Black Cotton Vertisol telemetry.",
    }
    ind_weather = {
        "t_max": 37.5,
        "t_min": 24.2,
        "rh": 55.0,
        "heat_thresh": 38.0,
        "conditions": "Hot & Partly Cloudy",
        "rain_daily": [0.0, 0.0, 4.5, 0.0, 0.0, 12.0, 1.0],
        "field_health_status": "watch",
        "driving_factors": [
            "Soil Health Score needs attention (62/100) due to low organic carbon",
            "Moderate heat stress forecast (2 days near 38°C thermal threshold)",
            "Vegetation vigor is Good (NDVI 0.64) with stable momentum",
        ],
        "derived_indicators": {
            "rainfall_anomaly_pct": -18.5,
            "heat_stress_days": 2,
            "critical_temp_threshold_c": 38.0,
            "frost_risk_level": "none",
            "frost_risk_days": 0,
            "drought_index": -0.85,
            "drought_class": "mild",
            "aridity_ratio_7d": 0.54,
            "disease_spread_weather_risk": 42,
            "irrigation_need_mm": 18.2,
            "best_spray_windows": ["Day 1", "Day 2", "Day 4", "Day 5"],
        },
        "notes": "Vidarbha semi-arid cotton agro-climatic baseline.",
    }

    ind_fixture, ind_png = build_farm_fixture(
        farm_id="farm-ind-vidarbha-01",
        field_id="field-ind-cotton-01",
        field_name="Patil North Cotton Plot",
        country_iso="IND",
        crop="cotton",
        lat=20.7453,
        lon=78.6022,
        base_ndvi=0.48,
        has_dip=False,
        soil_props=ind_soil,
        weather_props=ind_weather,
    )

    with open(os.path.join(fixtures_dir, "india_vidarbha_cotton.json"), "w", encoding="utf-8") as f:
        json.dump(ind_fixture, f, indent=2)
    with open(os.path.join(fixtures_dir, "india_vidarbha_cotton_ndvi.png"), "wb") as f:
        f.write(ind_png)
    print("  -> Created India Vidarbha Cotton fixture & PNG")

    # ------------------------------------------------------------------------
    # 2. BRAZIL (Mato Grosso Cerrado Oxisol Soybean with Stress Dip)
    # ------------------------------------------------------------------------
    bra_soil = {
        "texture_class": "Clay",
        "weighted": {
            "ph_h2o": 5.4,
            "soc_g_kg": 22.0,
            "nitrogen_g_kg": 1.85,
            "clay_pct": 52.0,
            "sand_pct": 28.0,
            "silt_pct": 20.0,
            "cec_cmol_kg": 7.2,
            "bulk_density_g_cm3": 1.18,
            "awhc_mm_per_m": 110.0,
        },
        "layers": {
            "phh2o": {"0-5cm": 5.6, "5-15cm": 5.4, "15-30cm": 5.2},
            "soc": {"0-5cm": 25.0, "5-15cm": 22.0, "15-30cm": 18.0},
            "nitrogen": {"0-5cm": 2.1, "5-15cm": 1.8, "15-30cm": 1.6},
            "clay": {"0-5cm": 50.0, "5-15cm": 52.0, "15-30cm": 54.0},
            "sand": {"0-5cm": 30.0, "5-15cm": 28.0, "15-30cm": 26.0},
            "silt": {"0-5cm": 20.0, "5-15cm": 20.0, "15-30cm": 20.0},
            "cec": {"0-5cm": 8.0, "5-15cm": 7.2, "15-30cm": 6.8},
            "bdod": {"0-5cm": 1.15, "5-15cm": 1.18, "15-30cm": 1.22},
        },
        "soil_health": {
            "total_score": 68,
            "health_class": "watch",
            "confidence": 0.94,
            "components": {
                "organic_carbon": {"score": 92.0, "weight": 25.0, "status": "healthy"},
                "ph_suitability": {"score": 52.0, "weight": 20.0, "status": "watch"},
                "nitrogen": {"score": 90.0, "weight": 15.0, "status": "healthy"},
                "texture_water": {"score": 75.0, "weight": 15.0, "status": "healthy"},
                "cec": {"score": 42.0, "weight": 15.0, "status": "risk"},
                "bulk_density": {"score": 90.0, "weight": 10.0, "status": "healthy"},
            },
            "limiting_factors": [
                "Soil acidity / low pH (5.4 in H2O) reduces phosphorus availability",
                "Low Cation Exchange Capacity (7.2 cmol/kg) causes potassium leaching",
                "Subsurface aluminium toxicity hazard in deeper subsoil layers",
            ],
            "plain_language_interpretation": "Deep well-structured Cerrado Oxisol with abundant organic carbon, but limited by low base saturation and subsoil acidity.",
            "quick_improvement_hints": [
                "Apply agricultural limestone (dolomitic lime) to neutralize exchangeable aluminium",
                "Broadcast agricultural gypsum to facilitate deep root penetration of calcium and sulfur",
                "Practice permanent cover cropping (Brachiaria ruziziensis) in off-season",
            ],
        },
        "notes": "Mato Grosso Sorriso Cerrado Latosolo Vermelho-Escuro.",
    }
    bra_weather = {
        "t_max": 31.8,
        "t_min": 22.4,
        "rh": 82.0,
        "heat_thresh": 35.0,
        "conditions": "Tropical Humid with Afternoon Showers",
        "rain_daily": [8.0, 14.5, 6.0, 18.2, 4.0, 2.0, 9.5],
        "field_health_status": "risk",
        "driving_factors": [
            "Elevated Asian soybean rust spore propagation risk (88/100) due to prolonged leaf wetness",
            "Satellite vegetation anomaly: 30-day stress dip (-12.4% vs 90d baseline) detected",
            "Soil pH is acidic (5.4) limiting active nodulation and nutrient uptake",
        ],
        "derived_indicators": {
            "rainfall_anomaly_pct": 24.2,
            "heat_stress_days": 0,
            "critical_temp_threshold_c": 35.0,
            "frost_risk_level": "none",
            "frost_risk_days": 0,
            "drought_index": 0.95,
            "drought_class": "none",
            "aridity_ratio_7d": 1.95,
            "disease_spread_weather_risk": 88,
            "irrigation_need_mm": 0.0,
            "best_spray_windows": ["Day 6 (brief morning window)"],
        },
        "notes": "Cerrado humid soybean agro-climatic baseline.",
    }

    bra_fixture, bra_png = build_farm_fixture(
        farm_id="farm-bra-sorriso-02",
        field_id="field-bra-soy-01",
        field_name="Talhão Sul Soja",
        country_iso="BRA",
        crop="soybean",
        lat=-12.5441,
        lon=-55.7214,
        base_ndvi=0.62,
        has_dip=True,  # Demonstrates visible anomaly detection!
        soil_props=bra_soil,
        weather_props=bra_weather,
    )

    with open(os.path.join(fixtures_dir, "brazil_cerrado_soybean.json"), "w", encoding="utf-8") as f:
        json.dump(bra_fixture, f, indent=2)
    with open(os.path.join(fixtures_dir, "brazil_cerrado_soybean_ndvi.png"), "wb") as f:
        f.write(bra_png)
    print("  -> Created Brazil Cerrado Soybean fixture & PNG (with stress anomaly dip)")

    # ------------------------------------------------------------------------
    # 3. SOUTH AFRICA (Free State Arenosol Maize)
    # ------------------------------------------------------------------------
    zaf_soil = {
        "texture_class": "Sandy Loam",
        "weighted": {
            "ph_h2o": 6.3,
            "soc_g_kg": 8.5,
            "nitrogen_g_kg": 0.78,
            "clay_pct": 14.0,
            "sand_pct": 72.0,
            "silt_pct": 14.0,
            "cec_cmol_kg": 9.5,
            "bulk_density_g_cm3": 1.52,
            "awhc_mm_per_m": 85.0,
        },
        "layers": {
            "phh2o": {"0-5cm": 6.4, "5-15cm": 6.3, "15-30cm": 6.2},
            "soc": {"0-5cm": 10.2, "5-15cm": 8.5, "15-30cm": 6.8},
            "nitrogen": {"0-5cm": 0.95, "5-15cm": 0.78, "15-30cm": 0.62},
            "clay": {"0-5cm": 12.0, "5-15cm": 14.0, "15-30cm": 16.0},
            "sand": {"0-5cm": 74.0, "5-15cm": 72.0, "15-30cm": 70.0},
            "silt": {"0-5cm": 14.0, "5-15cm": 14.0, "15-30cm": 14.0},
            "cec": {"0-5cm": 9.0, "5-15cm": 9.5, "15-30cm": 10.0},
            "bdod": {"0-5cm": 1.48, "5-15cm": 1.52, "15-30cm": 1.55},
        },
        "soil_health": {
            "total_score": 58,
            "health_class": "watch",
            "confidence": 0.90,
            "components": {
                "organic_carbon": {"score": 52.0, "weight": 25.0, "status": "watch"},
                "ph_suitability": {"score": 92.0, "weight": 20.0, "status": "healthy"},
                "nitrogen": {"score": 58.0, "weight": 15.0, "status": "watch"},
                "texture_water": {"score": 45.0, "weight": 15.0, "status": "risk"},
                "cec": {"score": 50.0, "weight": 15.0, "status": "watch"},
                "bulk_density": {"score": 52.0, "weight": 10.0, "status": "watch"},
            },
            "limiting_factors": [
                "Low Available Water-Holding Capacity (85 mm/m) due to 72% sand fraction",
                "High bulk density (1.52 g/cm³) indicating plow pan compaction",
                "High leaching vulnerability under intense storm events",
            ],
            "plain_language_interpretation": "Coarse-textured sandy loam with ideal neutral pH, but high vulnerability to drought stress and rapid nutrient drainage.",
            "quick_improvement_hints": [
                "Incorporate biochar or matured compost to enhance permanent water retention",
                "Maintain standing maize crop residue (stubble mulching) to reduce evaporative loss",
                "Split nitrogen applications into 3 fertigation doses to avoid leaching",
            ],
        },
        "notes": "Free State Highveld sandy loam / Arenosol telemetry.",
    }
    zaf_weather = {
        "t_max": 27.5,
        "t_min": 1.8,
        "rh": 38.0,
        "heat_thresh": 35.0,
        "conditions": "Sunny & Dry with Cold Night Frost Alert",
        "rain_daily": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.5],
        "field_health_status": "risk",
        "driving_factors": [
            "Frost alert: minimum temperatures approaching 1.8°C with moderate frost hazard",
            "Severe precipitation deficit: 7-day rainfall 2.5 mm vs ET0 demand 31.5 mm",
            "Soil water holding capacity is low (85 mm/m) causing rapid vegetative stress",
        ],
        "derived_indicators": {
            "rainfall_anomaly_pct": -65.0,
            "heat_stress_days": 0,
            "critical_temp_threshold_c": 35.0,
            "frost_risk_level": "moderate",
            "frost_risk_days": 2,
            "drought_index": -1.72,
            "drought_class": "severe",
            "aridity_ratio_7d": 0.08,
            "disease_spread_weather_risk": 15,
            "irrigation_need_mm": 28.5,
            "best_spray_windows": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"],
        },
        "notes": "South Africa Free State high-elevation maize climate baseline.",
    }

    zaf_fixture, zaf_png = build_farm_fixture(
        farm_id="farm-zaf-freestate-03",
        field_id="field-zaf-maize-01",
        field_name="Vrystaat West Mielies",
        country_iso="ZAF",
        crop="maize",
        lat=-27.9712,
        lon=26.7321,
        base_ndvi=0.42,
        has_dip=False,
        soil_props=zaf_soil,
        weather_props=zaf_weather,
    )

    with open(os.path.join(fixtures_dir, "south_africa_freestate_maize.json"), "w", encoding="utf-8") as f:
        json.dump(zaf_fixture, f, indent=2)
    with open(os.path.join(fixtures_dir, "south_africa_freestate_maize_ndvi.png"), "wb") as f:
        f.write(zaf_png)
    print("  -> Created South Africa Free State Maize fixture & PNG")

    print("\nAll 3 demo farm fixtures and NDVI heatmaps generated successfully!")


if __name__ == "__main__":
    main()
