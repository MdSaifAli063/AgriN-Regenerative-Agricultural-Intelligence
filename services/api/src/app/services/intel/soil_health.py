"""KrishiNet-BRICS - Soil Health Scoring Engine (0-100).

Pure, deterministic agronomic function evaluating physical, chemical, and biological
soil attributes based on the FAO/ISRIC Soil Health Framework.

Weights Summary (Sum = 100):
================================================================================
Component                     | Weight | Optimum Range       | Primary Deficit Risk
--------------------------------------------------------------------------------
Soil Organic Carbon (SOC)     |  25%   | 15.0 - 30.0+ g/kg   | Micro-biome starvation, erosion
pH Suitability (H2O)          |  20%   | 6.0 - 7.5 (crop)    | Nutrient lockup, Al/Na toxicity
Total Nitrogen (N)            |  15%   | 1.5 - 2.5+ g/kg     | Stunted vegetative biomass
Texture & Water Capacity      |  15%   | Loam / Clay Loam    | Drought vulnerability, pooling
Cation Exchange Capacity (CEC)|  15%   | 15.0 - 35.0 cmol/kg | Cation leaching, low buffering
Bulk Density (BDOD)           |  10%   | 1.10 - 1.35 g/cm³   | Subsoil compaction, root pans
================================================================================
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


class ComponentScore(BaseModel):
    name: str
    score: float = Field(..., description="Earned points for this component")
    max_weight: float = Field(..., description="Maximum possible points")
    percentage: float = Field(..., description="Normalized score 0.0 - 100.0%")
    status: Literal["healthy", "watch", "risk"] = Field(..., description="Status pill classification")
    measured_value: float = Field(..., description="Observed or estimated physical value")
    unit: str = Field(..., description="Measurement unit")
    optimum_range: str = Field(..., description="Agronomic benchmark range")
    impact_description: str = Field(..., description="Agronomic implication of current score")


class SoilHealthResult(BaseModel):
    total_score: int = Field(..., ge=0, le=100, description="Overall Soil Health Score (0 - 100)")
    health_class: Literal["Excellent", "Good", "Moderate", "Degraded"] = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence metric derived from input variance")
    components: Dict[str, ComponentScore] = Field(..., description="Individual component score breakdown")
    limiting_factors: List[str] = Field(..., description="Top 3 agronomic bottlenecks ranked by severity")
    plain_language_interpretation: str = Field(..., description="Actionable farmer-friendly summary")
    quick_improvement_hints: List[str] = Field(..., description="Top 3 organic-first regenerative actions")


def score_organic_carbon(soc_g_kg: float) -> Tuple[float, str]:
    """Scores Soil Organic Carbon (Weight: 25)."""
    val = max(0.0, soc_g_kg)
    if val < 5.0:
        ratio = (val / 5.0) * 0.40
        desc = "Severe organic deficit; vulnerable to structural collapse and low microbial activity."
    elif val < 15.0:
        ratio = 0.40 + ((val - 5.0) / 10.0) * 0.40
        desc = "Moderate organic matter; responsive to crop residue mulching and green manuring."
    elif val <= 30.0:
        ratio = 0.80 + ((val - 15.0) / 15.0) * 0.20
        desc = "Optimal organic carbon; healthy soil food web and high moisture buffering."
    else:
        ratio = 1.0
        desc = "Exceptional organic carbon density; high carbon sequestration."
    return round(ratio * 25.0, 2), desc


def score_ph(ph: float, crop: Optional[str] = None) -> Tuple[float, str]:
    """Scores soil pH suitability (Weight: 20), taking into account crop tolerances."""
    val = round(max(3.0, min(11.0, ph)), 2)
    crop_lower = (crop or "").lower()

    # Crop-specific pH optimum adjustments
    if any(c in crop_lower for c in ["cotton", "gram", "chickpea", "sorghum"]):
        opt_min, opt_max = 6.5, 8.2
    elif any(c in crop_lower for c in ["tea", "potato", "blueberry"]):
        opt_min, opt_max = 4.8, 6.2
    else:
        opt_min, opt_max = 6.0, 7.5

    if opt_min <= val <= opt_max:
        ratio = 1.0
        desc = f"Optimal pH ({val}) for maximum macro- and micronutrient bioavailability."
    elif val < opt_min:
        deficit = opt_min - val
        if deficit <= 0.6:
            ratio = 0.80
            desc = f"Slightly acidic ({val}); phosphorus fixation may begin."
        elif deficit <= 1.2:
            ratio = 0.55
            desc = f"Moderately acidic ({val}); risk of aluminum toxicity and calcium deficiency."
        else:
            ratio = max(0.10, 0.55 - (deficit - 1.2) * 0.3)
            desc = f"Strongly acidic ({val}); requires agricultural lime (CaCO3) amendment."
    else:
        excess = val - opt_max
        if excess <= 0.6:
            ratio = 0.80
            desc = f"Slightly alkaline ({val}); zinc and iron availability slightly reduced."
        elif excess <= 1.2:
            ratio = 0.55
            desc = f"Moderately alkaline/calcareous ({val}); micronutrient foliar sprays recommended."
        else:
            ratio = max(0.10, 0.55 - (excess - 1.2) * 0.3)
            desc = f"Strongly alkaline/sodic ({val}); risk of soil dispersion; gypsum amendment advised."

    return round(ratio * 20.0, 2), desc


def score_nitrogen(n_g_kg: float) -> Tuple[float, str]:
    """Scores Total Nitrogen (Weight: 15)."""
    val = max(0.0, n_g_kg)
    if val < 0.5:
        ratio = (val / 0.5) * 0.45
        desc = "Deficient nitrogen reservoir; high dependency on external inputs."
    elif val < 1.2:
        ratio = 0.45 + ((val - 0.5) / 0.7) * 0.35
        desc = "Moderate nitrogen reserve; benefit from legume intercropping."
    elif val <= 2.5:
        ratio = 0.80 + ((val - 1.2) / 1.3) * 0.20
        desc = "Good to optimal nitrogen status; supports vigorous early vegetative flush."
    else:
        ratio = 1.0
        desc = "Abundant total nitrogen reserve."
    return round(ratio * 15.0, 2), desc


def score_texture_and_awhc(clay_pct: float, sand_pct: float, silt_pct: float) -> Tuple[float, str]:
    """Scores Soil Texture & Available Water-Holding Capacity (Weight: 15)."""
    c, s, si = max(0.0, clay_pct), max(0.0, sand_pct), max(0.0, silt_pct)

    if s > 75.0:
        ratio = 0.50
        desc = f"Coarse Arenosol / Sand ({s:.1f}% sand); rapid drainage and high leaching risk."
    elif c > 55.0:
        ratio = 0.75
        desc = f"Heavy Vertisol / Clay ({c:.1f}% clay); massive water capacity, but prone to compaction and waterlogging."
    elif 18.0 <= c <= 35.0 and 20.0 <= s <= 50.0:
        ratio = 1.00
        desc = "Ideal Loam / Clay Loam matrix; superior soil aeration and available water retention."
    elif s > 50.0:
        ratio = 0.70
        desc = f"Sandy Loam ({s:.1f}% sand); responsive to organic mulch to improve moisture retention."
    else:
        ratio = 0.85
        desc = "Balanced medium-textured soil with favorable hydraulic conductivity."

    return round(ratio * 15.0, 2), desc


def score_cec(cec_cmol_kg: float) -> Tuple[float, str]:
    """Scores Cation Exchange Capacity (Weight: 15)."""
    val = max(0.0, cec_cmol_kg)
    if val < 6.0:
        ratio = (val / 6.0) * 0.40
        desc = "Very low CEC; poor retention of potassium, calcium, and magnesium cations."
    elif val < 15.0:
        ratio = 0.40 + ((val - 6.0) / 9.0) * 0.35
        desc = "Moderate CEC typical of weathered Oxisols; split nutrient application recommended."
    elif val <= 35.0:
        ratio = 0.75 + ((val - 15.0) / 20.0) * 0.25
        desc = "High cation exchange buffering; resilient against nutrient leaching."
    else:
        ratio = 1.0
        desc = "Exceptional nutrient buffering capacity (smectite/vermiculite clay dominant)."
    return round(ratio * 15.0, 2), desc


def score_bulk_density(bd_g_cm3: float) -> Tuple[float, str]:
    """Scores Soil Bulk Density / Compaction (Weight: 10)."""
    val = max(0.5, bd_g_cm3)
    if 1.10 <= val <= 1.35:
        ratio = 1.0
        desc = f"Ideal porosity and bulk density ({val:.2f} g/cm³); unhindered root penetration."
    elif val < 1.10:
        ratio = 0.85
        desc = f"Low bulk density ({val:.2f} g/cm³); highly porous or organic topsoil."
    elif val <= 1.50:
        ratio = 1.0 - ((val - 1.35) / 0.15) * 0.35
        desc = f"Moderate bulk density ({val:.2f} g/cm³); slight subsoil wheel-traffic compaction."
    elif val <= 1.70:
        ratio = 0.65 - ((val - 1.50) / 0.20) * 0.35
        desc = f"High bulk density ({val:.2f} g/cm³); restrictive to taproot elongation and infiltration."
    else:
        ratio = 0.20
        desc = f"Severe hardpan compaction ({val:.2f} g/cm³); mechanical or deep-taproot biological subsoiling required."
    return round(ratio * 10.0, 2), desc


def calculate_soil_health_score(
    ph: float,
    soc_g_kg: float,
    clay_pct: float,
    sand_pct: float,
    silt_pct: float,
    nitrogen_g_kg: Optional[float] = None,
    cec_cmol_kg: Optional[float] = None,
    bulk_density_g_cm3: Optional[float] = None,
    crop: Optional[str] = None,
    input_confidence: float = 0.90,
) -> SoilHealthResult:
    """
    Computes holistic 0-100 Soil Health Score with component breakdown and limiting factors.
    Pure mathematical function: 100% deterministic, side-effect free.
    """
    # Fallback plausible estimates if specific secondary properties are absent
    n_val = nitrogen_g_kg if nitrogen_g_kg is not None else max(0.2, soc_g_kg / 12.0)
    cec_val = cec_cmol_kg if cec_cmol_kg is not None else max(5.0, (clay_pct * 0.5) + (soc_g_kg * 0.2))
    bd_val = bulk_density_g_cm3 if bulk_density_g_cm3 is not None else max(1.1, 1.6 - (soc_g_kg * 0.015))

    # Calculate component scores
    soc_score, soc_desc = score_organic_carbon(soc_g_kg)
    ph_score, ph_desc = score_ph(ph, crop)
    n_score, n_desc = score_nitrogen(n_val)
    tex_score, tex_desc = score_texture_and_awhc(clay_pct, sand_pct, silt_pct)
    cec_score, cec_desc = score_cec(cec_val)
    bd_score, bd_desc = score_bulk_density(bd_val)

    def get_status(earned: float, max_w: float) -> Literal["healthy", "watch", "risk"]:
        pct = (earned / max_w) * 100.0
        if pct >= 80.0:
            return "healthy"
        if pct >= 55.0:
            return "watch"
        return "risk"

    components = {
        "organic_carbon": ComponentScore(
            name="Soil Organic Carbon (SOC)",
            score=soc_score,
            max_weight=25.0,
            percentage=round((soc_score / 25.0) * 100.0, 1),
            status=get_status(soc_score, 25.0),
            measured_value=round(soc_g_kg, 2),
            unit="g/kg",
            optimum_range="15.0 - 30.0 g/kg",
            impact_description=soc_desc,
        ),
        "ph_suitability": ComponentScore(
            name="pH Chemistry Suitability",
            score=ph_score,
            max_weight=20.0,
            percentage=round((ph_score / 20.0) * 100.0, 1),
            status=get_status(ph_score, 20.0),
            measured_value=round(ph, 2),
            unit="pH",
            optimum_range="6.0 - 7.5",
            impact_description=ph_desc,
        ),
        "total_nitrogen": ComponentScore(
            name="Total Nitrogen (N)",
            score=n_score,
            max_weight=15.0,
            percentage=round((n_score / 15.0) * 100.0, 1),
            status=get_status(n_score, 15.0),
            measured_value=round(n_val, 2),
            unit="g/kg",
            optimum_range="1.2 - 2.5 g/kg",
            impact_description=n_desc,
        ),
        "texture_water": ComponentScore(
            name="Texture & Water-Holding Matrix",
            score=tex_score,
            max_weight=15.0,
            percentage=round((tex_score / 15.0) * 100.0, 1),
            status=get_status(tex_score, 15.0),
            measured_value=round(clay_pct, 1),
            unit="% clay",
            optimum_range="18.0 - 35.0% clay",
            impact_description=tex_desc,
        ),
        "cation_exchange": ComponentScore(
            name="Cation Exchange Capacity (CEC)",
            score=cec_score,
            max_weight=15.0,
            percentage=round((cec_score / 15.0) * 100.0, 1),
            status=get_status(cec_score, 15.0),
            measured_value=round(cec_val, 1),
            unit="cmol/kg",
            optimum_range="15.0 - 35.0 cmol/kg",
            impact_description=cec_desc,
        ),
        "bulk_density": ComponentScore(
            name="Bulk Density & Porosity",
            score=bd_score,
            max_weight=10.0,
            percentage=round((bd_score / 10.0) * 100.0, 1),
            status=get_status(bd_score, 10.0),
            measured_value=round(bd_val, 2),
            unit="g/cm³",
            optimum_range="1.10 - 1.35 g/cm³",
            impact_description=bd_desc,
        ),
    }

    # Sum total score (clamped between 0 and 100)
    raw_total = sum(c.score for c in components.values())
    total_score = int(round(max(0.0, min(100.0, raw_total))))

    if total_score >= 80:
        health_class = "Excellent"
        summary = (
            f"Soil Health is rated EXCELLENT ({total_score}/100). The soil exhibits strong biological and "
            f"structural resilience. Maintain current regenerative practices and continuous groundcover."
        )
    elif total_score >= 65:
        health_class = "Good"
        summary = (
            f"Soil Health is rated GOOD ({total_score}/100). Favorable production conditions with minor "
            f"limiting factors that can be addressed via targeted biological amendments."
        )
    elif total_score >= 50:
        health_class = "Moderate"
        summary = (
            f"Soil Health is rated MODERATE ({total_score}/100). Key chemical or physical constraints "
            f"limit yield potential. Targeted regenerative remediation advised to build organic resilience."
        )
    else:
        health_class = "Degraded"
        summary = (
            f"Soil Health is rated DEGRADED ({total_score}/100). Severe nutrient or structural limitations "
            f"threaten crop stability. Prioritize restorative organic cover and soil restructuring."
        )

    # Rank limiting factors by relative shortfall
    def shortfall(c: ComponentScore) -> float:
        return (c.max_weight - c.score) / c.max_weight

    sorted_components = sorted(components.values(), key=shortfall, reverse=True)
    limiting_factors = [
        f"{c.name}: {c.impact_description}" for c in sorted_components if c.status in ["watch", "risk"]
    ][:3]

    if not limiting_factors:
        limiting_factors = ["No severe limiting factors identified; soil profile is well-balanced."]

    # Generate organic-first regenerative hints
    hints: List[str] = []
    top_limit = sorted_components[0]
    if top_limit.name.startswith("Soil Organic Carbon"):
        hints.append("Incorporate 5-8 t/ha of well-decomposed Farmyard Manure (FYM) or vermicompost before sowing.")
        hints.append("Practice in-situ crop residue retention (mulching) rather than burning or complete removal.")
        hints.append("Introduce multi-species cover crops (e.g. cowpea, sunn hemp, or brachiaria) during fallow windows.")
    elif top_limit.name.startswith("pH"):
        if ph < 6.0:
            hints.append("Apply agricultural lime (calcium carbonate) or dolomite to neutralize active topsoil acidity.")
            hints.append("Incorporate wood ash or biochar to elevate buffering capacity without salt accumulation.")
            hints.append("Favor acid-tolerant crop cultivars and mycorrhizal bio-inoculants to boost P-uptake.")
        else:
            hints.append("Apply agricultural gypsum (calcium sulphate) to displace excess exchangeable sodium.")
            hints.append("Use organic humic/fulvic acid drenches to liberate phosphorus locked in calcareous matrices.")
            hints.append("Apply sulfur-amended compost to gently lower rhizosphere pH around the root zone.")
    elif top_limit.name.startswith("Total Nitrogen"):
        hints.append("Seed-treat pulses or cereals with Rhizobium or Azotobacter biological nitrogen fixers.")
        hints.append("Intercrop a nitrogen-fixing pulse (e.g. pigeonpea, chickpea, or cowpea) at a 4:1 row ratio.")
        hints.append("Split top-dressed nitrogen into multiple smaller applications to match vegetative uptake peaks.")
    elif top_limit.name.startswith("Bulk Density"):
        hints.append("Avoid heavy machinery wheel-traffic when soil moisture exceeds field capacity.")
        hints.append("Cultivate deep taproot cover crops (e.g. tillage radish or daikon) for biological subsoiling.")
        hints.append("Transition to minimal tillage or direct-seeding (no-till) to rebuild macro-aggregate porosity.")
    else:
        hints.append("Maintain continuous organic living roots in the soil for at least 280 days per calendar year.")
        hints.append("Diversify crop rotation with deep-rooting and shallow-rooting species in alternating seasons.")
        hints.append("Apply balanced microbial inoculants (Trichoderma + Pseudomonas) to stimulate mycorrhizal hyphae.")

    # Ensure exactly 3 hints
    if len(hints) < 3:
        hints.append("Monitor soil moisture status before irrigating to prevent nutrient leaching.")

    return SoilHealthResult(
        total_score=total_score,
        health_class=health_class,
        confidence=round(input_confidence, 2),
        components=components,
        limiting_factors=limiting_factors,
        plain_language_interpretation=summary,
        quick_improvement_hints=hints[:3],
    )
