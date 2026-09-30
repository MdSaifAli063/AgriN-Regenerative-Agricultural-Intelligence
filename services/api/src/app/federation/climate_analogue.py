"""
KrishiNet-BRICS - Climate-Analogue Matching Engine.
Finds cross-border agro-ecological twins across BRICS nations using multivariate
bioclimatic distance (thermal profiles, precipitation regimes, aridity indices, and soil taxonomy).
Identifies proven regenerative practices that succeeded in analogous regions.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brics import ClimateAnalogue
from app.models.federation import ExternalClimateSignature


# ---------------------------------------------------------------------------
# Bioclimatic Schemas
# ---------------------------------------------------------------------------

class ClimateProfile(BaseModel):
    district_name: str
    country_iso: str  # "IN", "BR", "ZA", "CN", "RU"
    lat: float
    lon: float
    monthly_tmax: List[float] = Field(..., min_length=12, max_length=12)
    monthly_tmin: List[float] = Field(..., min_length=12, max_length=12)
    monthly_precip: List[float] = Field(..., min_length=12, max_length=12)  # mm
    aridity_index: float  # P / PET ratio (e.g. 0.45 = semi-arid)
    growing_degree_days: float  # Base 10°C
    soil_texture_class: str  # "Clay (Vertisol)", "Clay Loam (Oxisol)", "Sandy Clay Loam", etc.
    soil_ph_band: str  # "acidic", "neutral", "alkaline"
    proven_practices: List[Dict[str, Any]] = Field(default_factory=list)


class AnalogueMatchResult(BaseModel):
    source_region: str
    source_country: str
    analogue_region: str
    analogue_country: str
    similarity_index: float  # 0.0 to 1.0 (e.g. 0.88 = 88% climate similarity)
    temperature_match_score: float
    precipitation_match_score: float
    aridity_match_score: float
    soil_match_score: float
    hemisphere_aligned: bool
    bioclimatic_rationale: str
    successful_regenerative_practices: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Curated Seed Knowledgebase of BRICS Agricultural Districts
# ---------------------------------------------------------------------------

SEEDED_BRICS_PROFILES: List[ClimateProfile] = [
    ClimateProfile(
        district_name="Maharashtra (Vidarbha/Marathwada)",
        country_iso="IN",
        lat=20.59,
        lon=78.96,
        monthly_tmax=[29.0, 32.5, 37.0, 41.5, 43.0, 37.5, 31.0, 29.5, 31.0, 32.5, 30.5, 28.5],
        monthly_tmin=[13.0, 15.5, 19.5, 24.5, 27.5, 25.0, 23.5, 23.0, 22.5, 19.5, 15.0, 12.5],
        monthly_precip=[8.0, 6.0, 12.0, 10.0, 14.0, 175.0, 260.0, 210.0, 140.0, 50.0, 15.0, 5.0],
        aridity_index=0.48,
        growing_degree_days=2650.0,
        soil_texture_class="Clay (Vertisol / Black Cotton)",
        soil_ph_band="alkaline",
        proven_practices=[
            {
                "practice": "Broad Bed Furrow (BBF) + Pigeonpea Intercropping",
                "impact_summary": "+24% soil moisture retention during dry spells; +18% net revenue",
                "carbon_benefit_t_ha_yr": 0.42,
                "water_saved_m3_ha_yr": 380.0,
            },
            {
                "practice": "Cotton Stalk Biochar Soil Amendment",
                "impact_summary": "Doubles cation exchange capacity on alkaline vertisols; locks carbon",
                "carbon_benefit_t_ha_yr": 0.85,
                "water_saved_m3_ha_yr": 220.0,
            },
        ],
    ),
    ClimateProfile(
        district_name="Mato Grosso (Cerrado Basin)",
        country_iso="BR",
        lat=-12.68,
        lon=-55.72,
        # Southern hemisphere: warm year-round, distinct wet (Oct-Apr) / dry (May-Sep)
        monthly_tmax=[31.5, 31.8, 32.0, 32.5, 32.0, 32.2, 33.5, 35.5, 36.0, 34.0, 32.5, 31.8],
        monthly_tmin=[21.5, 21.6, 21.5, 21.0, 19.5, 17.5, 17.0, 18.5, 21.5, 22.0, 21.8, 21.6],
        monthly_precip=[280.0, 275.0, 240.0, 110.0, 30.0, 8.0, 4.0, 12.0, 55.0, 160.0, 210.0, 265.0],
        aridity_index=0.62,
        growing_degree_days=2900.0,
        soil_texture_class="Clay Loam (Oxisol / Latosol)",
        soil_ph_band="neutral",
        proven_practices=[
            {
                "practice": "No-Till + Brachiaria Grass Cover Crop Rotation",
                "impact_summary": "Continuous soil coverage shields against heat-stress; reduces herbicide by 40%",
                "carbon_benefit_t_ha_yr": 0.68,
                "water_saved_m3_ha_yr": 450.0,
            },
            {
                "practice": "Biological Nitrogen Fixation (Bradyrhizobium + Azospirillum inoculants)",
                "impact_summary": "Replaces 80kg/ha chemical urea; prevents soil acidification",
                "carbon_benefit_t_ha_yr": 0.55,
                "water_saved_m3_ha_yr": 190.0,
            },
            {
                "practice": "Integrated Crop-Livestock-Forestry (ILPF)",
                "impact_summary": "Eucalyptus shade strips lower ambient soil surface temperature by 4°C",
                "carbon_benefit_t_ha_yr": 1.95,
                "water_saved_m3_ha_yr": 610.0,
            },
        ],
    ),
    ClimateProfile(
        district_name="Free State (Maize Triangle)",
        country_iso="ZA",
        lat=-28.45,
        lon=26.78,
        monthly_tmax=[29.0, 28.0, 26.0, 22.0, 19.0, 16.0, 17.0, 20.0, 24.0, 26.5, 27.5, 28.5],
        monthly_tmin=[15.0, 14.5, 12.5, 8.0, 3.5, 0.5, 0.8, 3.2, 7.5, 11.0, 13.0, 14.5],
        monthly_precip=[85.0, 75.0, 65.0, 35.0, 15.0, 8.0, 5.0, 8.0, 20.0, 48.0, 68.0, 78.0],
        aridity_index=0.42,
        growing_degree_days=2100.0,
        soil_texture_class="Sandy Clay Loam",
        soil_ph_band="neutral",
        proven_practices=[
            {
                "practice": "Ultra-High Residue Stubble Mulching",
                "impact_summary": "Retains topsoil against wind erosion during semi-arid winter dormancy",
                "carbon_benefit_t_ha_yr": 0.38,
                "water_saved_m3_ha_yr": 310.0,
            },
            {
                "practice": "Drought-Resilient Cowpea Strip Cropping",
                "impact_summary": "Nutritional diversification and soil nitrogen recharge for following maize crop",
                "carbon_benefit_t_ha_yr": 0.44,
                "water_saved_m3_ha_yr": 260.0,
            },
        ],
    ),
    ClimateProfile(
        district_name="Heilongjiang (Songnen Plain)",
        country_iso="CN",
        lat=46.75,
        lon=126.55,
        monthly_tmax=[-12.0, -6.0, 3.0, 14.0, 22.0, 27.0, 28.5, 26.5, 20.5, 11.5, -1.0, -10.0],
        monthly_tmin=[-23.0, -18.0, -8.0, 2.0, 9.5, 16.0, 19.5, 17.5, 9.5, 1.0, -10.0, -20.0],
        monthly_precip=[4.0, 5.0, 10.0, 22.0, 45.0, 85.0, 140.0, 115.0, 55.0, 22.0, 10.0, 5.0],
        aridity_index=0.55,
        growing_degree_days=1750.0,
        soil_texture_class="Mollisol (Black Soil)",
        soil_ph_band="neutral",
        proven_practices=[
            {
                "practice": "Straw Return + Subsoiling Ridge Tillage",
                "impact_summary": "Protects black soil thickness against water runoff and freeze-thaw erosion",
                "carbon_benefit_t_ha_yr": 0.58,
                "water_saved_m3_ha_yr": 290.0,
            }
        ],
    ),
]


# ---------------------------------------------------------------------------
# Matching Engine
# ---------------------------------------------------------------------------

class ClimateAnalogueMatcher:
    """
    Multivariate Bioclimatic Distance Engine.
    Implements hemispheric season alignment, moisture index scaling, and soil compatibility scoring.
    """

    def __init__(self, additional_profiles: Optional[List[ClimateProfile]] = None):
        self.profiles: List[ClimateProfile] = list(SEEDED_BRICS_PROFILES)
        if additional_profiles:
            self.profiles.extend(additional_profiles)

    @staticmethod
    def _align_seasons(
        source_lat: float,
        target_lat: float,
        values: List[float],
    ) -> Tuple[List[float], bool]:
        """
        If source and target are in opposite hemispheres (cross-equatorial),
        shift the target's 12-month calendar by 6 months so summer aligns with summer.
        """
        cross_hemisphere = (source_lat * target_lat) < 0
        if cross_hemisphere:
            # Shift by 6 months (indices 6..11 then 0..5)
            shifted = values[6:] + values[:6]
            return shifted, True
        return list(values), False

    def compute_similarity(
        self,
        source: ClimateProfile,
        candidate: ClimateProfile,
    ) -> AnalogueMatchResult:
        """
        Calculate composite agro-ecological similarity score in range [0.0, 1.0].
        Weights:
          - Temperature Profile (Tmax & Tmin): 35%
          - Precipitation Regime (Monthly distribution): 35%
          - Aridity & Moisture Index: 15%
          - Soil Texture & pH Band: 15%
        """
        # 1. Align candidate calendar if cross-hemisphere
        cand_tmax, shifted = self._align_seasons(source.lat, candidate.lat, candidate.monthly_tmax)
        cand_tmin, _ = self._align_seasons(source.lat, candidate.lat, candidate.monthly_tmin)
        cand_precip, _ = self._align_seasons(source.lat, candidate.lat, candidate.monthly_precip)

        # 2. Temperature match score
        rmse_tmax = math.sqrt(np.mean((np.array(source.monthly_tmax) - np.array(cand_tmax)) ** 2))
        rmse_tmin = math.sqrt(np.mean((np.array(source.monthly_tmin) - np.array(cand_tmin)) ** 2))
        avg_temp_error = (rmse_tmax + rmse_tmin) / 2.0
        # 0 error -> 1.0, 15°C error -> 0.0
        temp_score = max(0.0, min(1.0, 1.0 - (avg_temp_error / 15.0)))

        # 3. Precipitation regime score (correlation + annual total match)
        src_p = np.array(source.monthly_precip, dtype=np.float64)
        tgt_p = np.array(cand_precip, dtype=np.float64)

        # Correlation of monthly rainfall curve
        if np.std(src_p) > 1e-4 and np.std(tgt_p) > 1e-4:
            r = float(np.corrcoef(src_p, tgt_p)[0, 1])
            pattern_score = max(0.0, (r + 1.0) / 2.0)  # map [-1, 1] to [0, 1]
        else:
            pattern_score = 0.5

        # Total rainfall magnitude similarity
        total_src = float(np.sum(src_p))
        total_tgt = float(np.sum(tgt_p))
        ratio = min(total_src, total_tgt) / max(total_src, total_tgt, 1.0)
        precip_score = 0.6 * pattern_score + 0.4 * ratio

        # 4. Aridity Index match score
        aridity_diff = abs(source.aridity_index - candidate.aridity_index)
        aridity_score = max(0.0, min(1.0, 1.0 - (aridity_diff / 0.50)))

        # 5. Soil compatibility score
        soil_score = 0.50  # baseline
        if source.soil_ph_band == candidate.soil_ph_band:
            soil_score += 0.25
        if source.soil_texture_class.split()[0].lower() in candidate.soil_texture_class.lower():
            soil_score += 0.25

        # Weighted composite similarity
        composite = (
            0.35 * temp_score
            + 0.35 * precip_score
            + 0.15 * aridity_score
            + 0.15 * soil_score
        )
        composite = round(float(min(0.99, max(0.10, composite))), 3)

        rationale = (
            f"Analogue identified between {source.district_name} ({source.country_iso}) and "
            f"{candidate.district_name} ({candidate.country_iso}). "
            f"Thermal profile alignment: {temp_score*100:.1f}%, Precipitation regime match: {precip_score*100:.1f}%, "
            f"Aridity similarity: {aridity_score*100:.1f}%. "
            f"{'Hemispheric 6-month seasonal cycle shifted for equatorial alignment. ' if shifted else ''}"
            f"Shared agronomic challenges allow bilateral transfer of regenerative practices."
        )

        return AnalogueMatchResult(
            source_region=source.district_name,
            source_country=source.country_iso,
            analogue_region=candidate.district_name,
            analogue_country=candidate.country_iso,
            similarity_index=composite,
            temperature_match_score=round(temp_score, 3),
            precipitation_match_score=round(precip_score, 3),
            aridity_match_score=round(aridity_score, 3),
            soil_match_score=round(soil_score, 3),
            hemisphere_aligned=shifted,
            bioclimatic_rationale=rationale,
            successful_regenerative_practices=candidate.proven_practices,
        )

    async def match(
        self,
        query_profile: ClimateProfile,
        db: Optional[AsyncSession] = None,
        top_k: int = 3,
        min_similarity: float = 0.30,
        exclude_same_country: bool = False,
    ) -> List[AnalogueMatchResult]:
        """
        Find top-K climate analogue matches from both seeded database and
        inbound `external_climate_signatures` received from peer BRICS nodes.
        """
        candidates: List[ClimateProfile] = [p for p in self.profiles]

        # Load live partner signatures if DB available
        if db:
            stmt = select(ExternalClimateSignature)
            res = await db.execute(stmt)
            external_rows = res.scalars().all()
            for ext in external_rows:
                candidates.append(
                    ClimateProfile(
                        district_name=ext.district_name,
                        country_iso=ext.origin_country_iso,
                        lat=ext.centroid_lat,
                        lon=ext.centroid_lon,
                        monthly_tmax=ext.monthly_tmax,
                        monthly_tmin=ext.monthly_tmin,
                        monthly_precip=ext.monthly_precip,
                        aridity_index=ext.aridity_index,
                        growing_degree_days=ext.growing_degree_days,
                        soil_texture_class=ext.soil_texture_class,
                        soil_ph_band=ext.soil_ph_band,
                        proven_practices=[{"practice": p} for p in ext.proven_practices],
                    )
                )

        matches: List[AnalogueMatchResult] = []
        for cand in candidates:
            # Skip self-match
            if cand.district_name == query_profile.district_name and cand.country_iso == query_profile.country_iso:
                continue
            if exclude_same_country and cand.country_iso == query_profile.country_iso:
                continue

            match_res = self.compute_similarity(query_profile, cand)
            if match_res.similarity_index >= min_similarity:
                matches.append(match_res)

        matches.sort(key=lambda m: m.similarity_index, reverse=True)
        top_matches = matches[:top_k]

        # Persist to database if session provided
        if db:
            for m in top_matches:
                analogue_row = ClimateAnalogue(
                    id=str(uuid.uuid4()),
                    source_region=m.source_region,
                    source_country=m.source_country,
                    analogue_region=m.analogue_region,
                    analogue_country=m.analogue_country,
                    similarity_index=m.similarity_index,
                    successful_regenerative_practices=m.successful_regenerative_practices,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(analogue_row)
            await db.commit()

        return top_matches
