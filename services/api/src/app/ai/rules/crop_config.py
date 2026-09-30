"""
KrishiNet-BRICS - Agronomic Crop Specification & Biophysical Limits Registry.

Maintains biophysical envelopes for crop suitability scoring:
  - Thermal thresholds, base temperatures, and heat stress ceilings
  - Optimal and absolute soil pH chemistry bounds
  - Preferred USDA soil texture classes
  - Seasonal water requirements and FAO-56 crop coefficients (Kc)
  - Plausible yield ranges and season durations across BRICS climates
"""

from typing import Dict, List, NamedTuple, Optional, Tuple


class CropSpec(NamedTuple):
    name: str
    optimal_ph_range: Tuple[float, float]
    absolute_ph_range: Tuple[float, float]
    optimal_temp_c: Tuple[float, float]
    heat_stress_threshold_c: float
    frost_tolerance: str  # "none", "low", "moderate", "high"
    min_rainfall_mm: float
    max_rainfall_mm: float
    seasonal_water_need_mm: int
    water_need_level: str  # "low", "medium", "high"
    season_days_range: Tuple[int, int]
    preferred_textures: List[str]
    typical_yield_t_ha: Tuple[float, float]
    kc_mid_season: float
    description: str


CROP_AGRONOMIC_SPECS: Dict[str, CropSpec] = {
    "cotton": CropSpec(
        name="Cotton",
        optimal_ph_range=(6.5, 8.2),
        absolute_ph_range=(5.5, 8.8),
        optimal_temp_c=(22.0, 32.0),
        heat_stress_threshold_c=38.0,
        frost_tolerance="none",
        min_rainfall_mm=500.0,
        max_rainfall_mm=1100.0,
        seasonal_water_need_mm=700,
        water_need_level="medium",
        season_days_range=(140, 180),
        preferred_textures=["Clay", "Clay Loam", "Silty Clay", "Loam"],
        typical_yield_t_ha=(1.8, 3.2),
        kc_mid_season=1.15,
        description="Deep-rooted taproot crop; thrives in black Vertisols with high moisture retention.",
    ),
    "soybean": CropSpec(
        name="Soybean",
        optimal_ph_range=(5.5, 7.0),
        absolute_ph_range=(5.0, 7.8),
        optimal_temp_c=(20.0, 30.0),
        heat_stress_threshold_c=35.0,
        frost_tolerance="none",
        min_rainfall_mm=450.0,
        max_rainfall_mm=850.0,
        seasonal_water_need_mm=600,
        water_need_level="medium",
        season_days_range=(105, 130),
        preferred_textures=["Clay Loam", "Loam", "Sandy Clay Loam", "Clay"],
        typical_yield_t_ha=(2.5, 4.5),
        kc_mid_season=1.15,
        description="N-fixing legume; optimal in Cerrado Latosols with Bradyrhizobium inoculation.",
    ),
    "maize": CropSpec(
        name="Maize",
        optimal_ph_range=(5.8, 7.5),
        absolute_ph_range=(5.2, 8.2),
        optimal_temp_c=(18.0, 32.0),
        heat_stress_threshold_c=35.0,
        frost_tolerance="low",
        min_rainfall_mm=500.0,
        max_rainfall_mm=950.0,
        seasonal_water_need_mm=750,
        water_need_level="high",
        season_days_range=(110, 145),
        preferred_textures=["Sandy Loam", "Loam", "Silt Loam", "Clay Loam"],
        typical_yield_t_ha=(4.0, 9.5),
        kc_mid_season=1.20,
        description="C4 cereal; responsive to conservation agriculture, stubble mulch, and pivot irrigation.",
    ),
    "pigeonpea": CropSpec(
        name="Pigeon Pea",
        optimal_ph_range=(6.0, 8.2),
        absolute_ph_range=(5.5, 8.5),
        optimal_temp_c=(20.0, 35.0),
        heat_stress_threshold_c=40.0,
        frost_tolerance="none",
        min_rainfall_mm=400.0,
        max_rainfall_mm=900.0,
        seasonal_water_need_mm=500,
        water_need_level="low",
        season_days_range=(150, 200),
        preferred_textures=["Clay", "Clay Loam", "Loam"],
        typical_yield_t_ha=(1.0, 2.2),
        kc_mid_season=1.05,
        description="Deep-rooted drought-hardy legume; exceptional companion for cotton intercropping.",
    ),
    "sorghum": CropSpec(
        name="Sorghum",
        optimal_ph_range=(5.5, 8.2),
        absolute_ph_range=(5.0, 8.8),
        optimal_temp_c=(22.0, 35.0),
        heat_stress_threshold_c=40.0,
        frost_tolerance="low",
        min_rainfall_mm=350.0,
        max_rainfall_mm=750.0,
        seasonal_water_need_mm=450,
        water_need_level="low",
        season_days_range=(100, 130),
        preferred_textures=["Sandy Loam", "Loam", "Clay Loam", "Clay"],
        typical_yield_t_ha=(2.5, 5.5),
        kc_mid_season=1.05,
        description="Highly drought and heat tolerant C4 cereal; excels as rotation crop.",
    ),
    "sunflower": CropSpec(
        name="Sunflower",
        optimal_ph_range=(6.0, 7.5),
        absolute_ph_range=(5.5, 8.0),
        optimal_temp_c=(18.0, 30.0),
        heat_stress_threshold_c=36.0,
        frost_tolerance="moderate",
        min_rainfall_mm=400.0,
        max_rainfall_mm=800.0,
        seasonal_water_need_mm=550,
        water_need_level="medium",
        season_days_range=(90, 120),
        preferred_textures=["Sandy Loam", "Loam", "Clay Loam"],
        typical_yield_t_ha=(1.5, 3.0),
        kc_mid_season=1.10,
        description="Extensive taproot scavenger; extracts deep subsoil nutrients and residual moisture.",
    ),
    "wheat": CropSpec(
        name="Wheat",
        optimal_ph_range=(6.0, 7.5),
        absolute_ph_range=(5.5, 8.2),
        optimal_temp_c=(15.0, 24.0),
        heat_stress_threshold_c=30.0,
        frost_tolerance="high",
        min_rainfall_mm=400.0,
        max_rainfall_mm=750.0,
        seasonal_water_need_mm=500,
        water_need_level="medium",
        season_days_range=(110, 140),
        preferred_textures=["Loam", "Clay Loam", "Silt Loam"],
        typical_yield_t_ha=(3.0, 6.5),
        kc_mid_season=1.15,
        description="Cool-season cereal; sensitive to terminal heat above 30°C during grain filling.",
    ),
    "cowpea": CropSpec(
        name="Cowpea",
        optimal_ph_range=(5.5, 7.5),
        absolute_ph_range=(5.0, 8.0),
        optimal_temp_c=(22.0, 35.0),
        heat_stress_threshold_c=40.0,
        frost_tolerance="none",
        min_rainfall_mm=300.0,
        max_rainfall_mm=700.0,
        seasonal_water_need_mm=380,
        water_need_level="low",
        season_days_range=(65, 90),
        preferred_textures=["Sandy Loam", "Loam", "Sand"],
        typical_yield_t_ha=(1.0, 2.0),
        kc_mid_season=1.00,
        description="Short-duration high-protein pulse; excellent quick cover crop and green manure.",
    ),
}


def get_crop_spec(crop_name: str) -> Optional[CropSpec]:
    """Retrieves agronomic specification for a given crop name."""
    clean = crop_name.lower().strip()
    return CROP_AGRONOMIC_SPECS.get(clean)
