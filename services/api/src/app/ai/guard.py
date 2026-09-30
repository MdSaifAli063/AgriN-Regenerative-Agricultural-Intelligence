"""
KrishiNet-BRICS - Confidence Scoring, Hallucination Guard & Advisory Verifier.

Implements pure mathematical scoring, safety checks, and hard invariant enforcements:
  - 4-component weighted confidence formula:
      confidence = 0.30*data_quality + 0.25*retrieval_support + 0.25*self_consistency + 0.20*rules_agreement
  - Strict biophysical threshold tiers (HIGH >= 0.75, MEDIUM 0.55-0.75, LOW < 0.55)
  - Post-generation rule-based Verifier catching unsupported claims, out-of-range dates,
    bad citations, and rainfed irrigation contradictions
  - Hallucination Guard providing reduced, safe advisories and officer escalations for LOW confidence
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.ai.rules.crop_config import CROP_AGRONOMIC_SPECS
from app.ai.rules.engine import deterministic_rules_engine
from app.schemas.advisory import (
    AdvisoryConfidence,
    AdvisoryContract,
    Citation,
    ConfidenceComponents,
    ConfidenceLevel,
    RegenerativePracticeEnum,
)

logger = logging.getLogger("krishinet.ai.guard")

# Configurable Thresholds
CONFIDENCE_HIGH_THRESHOLD = 0.75
CONFIDENCE_LOW_THRESHOLD = 0.55


# ============================================================================
# 1. PURE MATHEMATICAL CONFIDENCE SCORING
# ============================================================================

def compute_confidence_score(
    data_quality: float,
    retrieval_support: float,
    self_consistency: float,
    rules_agreement: float,
) -> Tuple[float, ConfidenceComponents, ConfidenceLevel]:
    """
    Pure mathematical 4-component weighted confidence formula.
    Weights: Data Quality 30%, Retrieval Support 25%, Self-Consistency 25%, Rules Agreement 20%.
    """
    # Clamp all inputs to [0.0, 1.0]
    dq = max(0.0, min(1.0, float(data_quality)))
    rs = max(0.0, min(1.0, float(retrieval_support)))
    sc = max(0.0, min(1.0, float(self_consistency)))
    ra = max(0.0, min(1.0, float(rules_agreement)))

    overall = round((0.30 * dq) + (0.25 * rs) + (0.25 * sc) + (0.20 * ra), 3)

    if overall >= CONFIDENCE_HIGH_THRESHOLD:
        level = ConfidenceLevel.HIGH
    elif overall >= CONFIDENCE_LOW_THRESHOLD:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    components = ConfidenceComponents(
        data_quality=round(dq, 3),
        retrieval_support=round(rs, 3),
        model_self_consistency=round(sc, 3),
        agreement_with_rules=round(ra, 3),
    )

    return overall, components, level


def calculate_retrieval_support(
    retrieved_citations: List[Citation],
    contract: AdvisoryContract,
) -> float:
    """Calculates retrieval support from mean relevance score and citation coverage."""
    if not retrieved_citations:
        return 0.40  # Baseline penalty when no citations

    mean_score = sum(c.score for c in retrieved_citations) / len(retrieved_citations)

    # Citation coverage in recommendations
    total_recs = len(contract.crop_recommendations)
    cited_recs = sum(1 for r in contract.crop_recommendations if r.citations)
    coverage = (cited_recs / total_recs) if total_recs > 0 else 0.5

    return round((0.60 * mean_score) + (0.40 * coverage), 3)


def calculate_rules_agreement(
    llm_contract: AdvisoryContract,
    field_id: str,
    current_crop: str,
    irrigation_type: str,
    farm_country: str,
    soil_data: Optional[Dict[str, Any]] = None,
    weather_data: Optional[Dict[str, Any]] = None,
    satellite_data: Optional[Dict[str, Any]] = None,
) -> float:
    """Calculates agreement between LLM advisory and deterministic biophysical rules engine."""
    rules_advisory = deterministic_rules_engine.generate_advisory(
        field_id=field_id,
        current_crop=current_crop,
        irrigation_type=irrigation_type,
        farm_country=farm_country,
        soil_data=soil_data,
        weather_data=weather_data,
        satellite_data=satellite_data,
    )

    # 1. Top crops Jaccard agreement
    llm_crops = set(r.crop.lower() for r in llm_contract.crop_recommendations)
    rules_crops = set(r.crop.lower() for r in rules_advisory.crop_recommendations)

    intersection_crops = llm_crops.intersection(rules_crops)
    union_crops = llm_crops.union(rules_crops)
    crop_jaccard = (len(intersection_crops) / len(union_crops)) if union_crops else 0.5

    # 2. Practice category overlap
    llm_practices = set(p.practice.value for p in llm_contract.regenerative_practices)
    rules_practices = set(p.practice.value for p in rules_advisory.regenerative_practices)

    practice_overlap = (
        len(llm_practices.intersection(rules_practices)) / max(1, len(rules_practices))
    )

    return round((0.60 * crop_jaccard) + (0.40 * practice_overlap), 3)


# ============================================================================
# 2. RULE-BASED ADVISORY VERIFIER (POST-GENERATION CHECK)
# ============================================================================

class VerificationResult:
    def __init__(self, is_valid: bool, issues: List[str]):
        self.is_valid = is_valid
        self.issues = issues


class AdvisoryVerifier:
    """Rule-based verification checking biophysical constraints, citations, and ranges."""

    @classmethod
    def verify(
        cls,
        contract: AdvisoryContract,
        allowed_citation_ids: Set[str],
        irrigation_type: str = "rainfed",
    ) -> VerificationResult:
        issues = []

        # 1. Crop Validity: all crops must exist in CROP_AGRONOMIC_SPECS
        for rec in contract.crop_recommendations:
            if rec.crop.lower() not in CROP_AGRONOMIC_SPECS:
                issues.append(f"Crop '{rec.crop}' is unknown or not supported in agronomic catalog.")

        # 2. Citation Integrity: all citations must match provided retrieved passage IDs
        for rec in contract.crop_recommendations:
            for cit in rec.citations:
                if allowed_citation_ids and cit.doc_id not in allowed_citation_ids:
                    issues.append(f"Citation doc_id '{cit.doc_id}' on crop '{rec.crop}' was not in retrieved context.")

        for prac in contract.regenerative_practices:
            for cit in prac.citations:
                if allowed_citation_ids and cit.doc_id not in allowed_citation_ids:
                    issues.append(f"Citation doc_id '{cit.doc_id}' on practice '{prac.practice}' was not in retrieved context.")

        # 3. Irrigation Type Consistency: rainfed farms cannot be advised overhead pivot/flood irrigation
        if irrigation_type.lower() == "rainfed":
            for irr in contract.irrigation_schedule:
                method_val = getattr(irr, "method", None) or (irr.get("method") if isinstance(irr, dict) else "")
                method_lower = str(method_val).lower()
                if any(k in method_lower for k in ["pivot", "flood", "sprinkler", "canal"]):
                    issues.append(
                        f"Rainfed farm cannot be scheduled active irrigation method '{method_val}'. Must be moisture conservation only."
                    )

        # 4. Action Calendar Invariants: day offsets must be within 1-30 days
        for action in contract.action_calendar_30d:
            if action.day_offset < 1 or action.day_offset > 30:
                issues.append(f"Action '{action.title}' day_offset {action.day_offset} is outside 1-30 day window.")

        # 5. Ranges and Scores Invariants
        for rec in contract.crop_recommendations:
            if rec.suitability_score < 0 or rec.suitability_score > 100:
                issues.append(f"Crop '{rec.crop}' suitability score {rec.suitability_score} outside 0-100.")
            if rec.expected_yield_range.min > rec.expected_yield_range.max:
                issues.append(f"Crop '{rec.crop}' yield min ({rec.expected_yield_range.min}) exceeds max ({rec.expected_yield_range.max}).")

        is_valid = len(issues) == 0
        return VerificationResult(is_valid=is_valid, issues=issues)


# ============================================================================
# 3. HALLUCINATION & CONFIDENCE GUARD
# ============================================================================

class HallucinationGuard:
    """
    Monitors advisory confidence and applies hard safety blocks and escalations.
    """

    @classmethod
    def apply_guard(
        cls,
        contract: AdvisoryContract,
        allowed_citation_ids: Set[str],
        irrigation_type: str = "rainfed",
    ) -> AdvisoryContract:
        """
        Applies verifier, hard-blocks unsupported claims, and reduces low-confidence advisories.
        """
        # 1. Hard Blocks (sanitizing unsupported crops or contradictory rainfed irrigation)
        valid_crops = [
            r for r in contract.crop_recommendations
            if r.crop.lower() in CROP_AGRONOMIC_SPECS
        ]
        if not valid_crops:
            # Fallback to cotton or default if all crops were invalid
            spec = CROP_AGRONOMIC_SPECS["cotton"]
            valid_crops = [
                CropRecommendation(
                    crop="cotton",
                    suitability_score=75,
                    expected_yield_range=YieldRange(min=spec.typical_yield_t_ha[0], max=spec.typical_yield_t_ha[1]),
                    water_need=WaterNeed(level=spec.water_need_level, mm_per_season=spec.seasonal_water_need_mm),
                    climate_risk=ClimateRisk(level="low", drivers=[]),
                    why_it_fits="Standard biophysical candidate.",
                )
            ]
        contract.crop_recommendations = valid_crops

        # Strip invalid citations that do not exist in allowed context
        if allowed_citation_ids:
            for rec in contract.crop_recommendations:
                rec.citations = [c for c in rec.citations if c.doc_id in allowed_citation_ids]
            for prac in contract.regenerative_practices:
                prac.citations = [c for c in prac.citations if c.doc_id in allowed_citation_ids]

        # Enforce rainfed irrigation sanitization
        if irrigation_type.lower() == "rainfed":
            clean_irr = []
            for item in contract.irrigation_schedule:
                if not any(k in item.method.lower() for k in ["pivot", "flood", "sprinkler"]):
                    clean_irr.append(item)
            if not clean_irr:
                # Add rainfed moisture event
                clean_irr.append(
                    contract.irrigation_schedule[0] if contract.irrigation_schedule else None
                )
                if clean_irr[0]:
                    clean_irr[0].mm = 0.0
                    clean_irr[0].method = "In-situ moisture conservation / Mulch"
                    clean_irr[0].rationale = "Maintain residue cover to suppress evaporative loss on rainfed field."
            contract.irrigation_schedule = [i for i in clean_irr if i is not None]

        # 2. Check Confidence Level
        conf = contract.confidence
        if conf.overall < CONFIDENCE_LOW_THRESHOLD:
            logger.warning(f"Confidence score {conf.overall:.2f} is LOW (<{CONFIDENCE_LOW_THRESHOLD}); activating Guard.")
            contract.confidence.guard_triggered = True
            contract.confidence.level = ConfidenceLevel.LOW
            contract.confidence.escalation_message = (
                "Confidence is low for this field due to incomplete telemetry or high biophysical uncertainty. "
                "Do not apply mineral supplements or commercial crop transitions without consulting your local "
                "extension officer."
            )
            # Reduce advisory to safe, conservative guidance
            contract.field_summary = (
                f"[LOW CONFIDENCE ALERT] {contract.field_summary} "
                f"Data quality or retrieval coverage is insufficient for firm dosage recommendations."
            )
            # Restrict chemical mineral supplements
            contract.fertiliser_plan.mineral_supplement = (
                "HOLD MINERAL APPLICATIONS: Telemetry confidence is below threshold. "
                "Consult extension officer before applying synthetic fertilizers."
            )
        elif conf.overall < CONFIDENCE_HIGH_THRESHOLD:
            contract.confidence.level = ConfidenceLevel.MEDIUM
            contract.confidence.guard_triggered = False
            contract.confidence.escalation_message = (
                "Medium confidence advisory. Verify biophysical recommendations with local agronomy agent."
            )
        else:
            contract.confidence.level = ConfidenceLevel.HIGH
            contract.confidence.guard_triggered = False
            contract.confidence.escalation_message = None

        return contract


advisory_verifier = AdvisoryVerifier()
hallucination_guard = HallucinationGuard()
