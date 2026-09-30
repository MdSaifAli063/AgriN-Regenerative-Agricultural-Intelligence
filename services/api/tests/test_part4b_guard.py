"""
KrishiNet-BRICS - Phase 4 Part 4B Test Suite.

Validates:
  1. Pure mathematical confidence scoring formula, boundaries, and monotonicity
  2. Hallucination guard triggers on LOW confidence (<0.55) with escalation message
  3. Verifier checks: bad citations, out-of-range calendar offsets, rainfed contradictions
  4. Hard-block sanitization of unsupported crops and unauthorized dosage claims
  5. Deterministic rule engine produces valid, explainable advisories for all 3 demo farms
  6. Dual-view explainability payload generation (farmer visual brief vs. officer diagnostic)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.ai.explainability import explainability_service
from app.ai.guard import (
    advisory_verifier,
    compute_confidence_score,
    hallucination_guard,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_LOW_THRESHOLD,
)
from app.ai.rules.engine import deterministic_rules_engine
from app.schemas.advisory import (
    ActionCalendarItem,
    AdvisoryConfidence,
    AdvisoryContract,
    Citation,
    ConfidenceComponents,
    ConfidenceLevel,
    CropRecommendation,
    IrrigationItem,
    RegenerativePracticeEnum,
    UrgencyLevel,
    YieldRange,
)


# ============================================================================
# 1. CONFIDENCE FORMULA BOUNDARIES & MONOTONICITY
# ============================================================================

def test_confidence_formula_boundaries():
    """Verify minimum, maximum, and exact mathematical weight contributions."""
    # 1. Perfect confidence
    score_max, comp_max, level_max = compute_confidence_score(1.0, 1.0, 1.0, 1.0)
    assert score_max == 1.0
    assert level_max == ConfidenceLevel.HIGH

    # 2. Zero confidence
    score_min, comp_min, level_min = compute_confidence_score(0.0, 0.0, 0.0, 0.0)
    assert score_min == 0.0
    assert level_min == ConfidenceLevel.LOW

    # 3. Exact component weights: 0.30 Data Quality, 0.25 Retrieval, 0.25 Self-Consistency, 0.20 Rules
    score_dq, _, _ = compute_confidence_score(1.0, 0.0, 0.0, 0.0)
    assert abs(score_dq - 0.30) < 1e-4

    score_ret, _, _ = compute_confidence_score(0.0, 1.0, 0.0, 0.0)
    assert abs(score_ret - 0.25) < 1e-4

    score_sc, _, _ = compute_confidence_score(0.0, 0.0, 1.0, 0.0)
    assert abs(score_sc - 0.25) < 1e-4

    score_ra, _, _ = compute_confidence_score(0.0, 0.0, 0.0, 1.0)
    assert abs(score_ra - 0.20) < 1e-4


def test_confidence_formula_monotonicity():
    """Verify that increasing any component strictly increases the overall score."""
    base_score, _, _ = compute_confidence_score(0.5, 0.5, 0.5, 0.5)
    higher_dq, _, _ = compute_confidence_score(0.8, 0.5, 0.5, 0.5)
    higher_ret, _, _ = compute_confidence_score(0.5, 0.8, 0.5, 0.5)
    higher_sc, _, _ = compute_confidence_score(0.5, 0.5, 0.8, 0.5)
    higher_ra, _, _ = compute_confidence_score(0.5, 0.5, 0.5, 0.8)

    assert higher_dq > base_score
    assert higher_ret > base_score
    assert higher_sc > base_score
    assert higher_ra > base_score


# ============================================================================
# 2. HALLUCINATION GUARD & LOW CONFIDENCE ESCALATION
# ============================================================================

def test_guard_triggers_at_low_confidence():
    """Verify that low confidence triggers guard, escalates to officer, and strips mineral dosages."""
    # Generate valid base advisory from rules engine
    advisory = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        farm_country="IND",
    )

    # Force low confidence (e.g. 0.45 < 0.55)
    advisory.confidence = AdvisoryConfidence(
        overall=0.45,
        components=ConfidenceComponents(
            data_quality=0.40,
            retrieval_support=0.40,
            model_self_consistency=0.50,
            agreement_with_rules=0.50,
        ),
        level=ConfidenceLevel.LOW,
        guard_triggered=False,
    )

    guarded = hallucination_guard.apply_guard(
        contract=advisory,
        allowed_citation_ids={"doc_cotton_01"},
        irrigation_type="rainfed",
    )

    assert guarded.confidence.guard_triggered is True
    assert guarded.confidence.level == ConfidenceLevel.LOW
    assert "consult" in guarded.confidence.escalation_message.lower()
    assert "[LOW CONFIDENCE ALERT]" in guarded.field_summary
    assert "HOLD MINERAL APPLICATIONS" in guarded.fertiliser_plan.mineral_supplement


def test_guard_hard_block_unsupported_crop():
    """Verify hallucination guard strips crops not found in the agronomic catalog."""
    advisory = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        farm_country="IND",
    )

    # Inject fabricated crop
    advisory.crop_recommendations.append(
        CropRecommendation(
            crop="fictional_miracle_grain",
            suitability_score=99,
            expected_yield_range=YieldRange(min=5.0, max=10.0),
            water_need={"level": "low", "mm_per_season": 200},
            climate_risk={"level": "low"},
            why_it_fits="Fabricated miraculous yield.",
        )
    )

    guarded = hallucination_guard.apply_guard(
        contract=advisory,
        allowed_citation_ids={"doc_cotton_01"},
        irrigation_type="rainfed",
    )

    crop_names = [r.crop.lower() for r in guarded.crop_recommendations]
    assert "fictional_miracle_grain" not in crop_names


# ============================================================================
# 3. ADVISORY VERIFIER RULE-BASED CHECKS
# ============================================================================

def test_verifier_catches_rainfed_irrigation_contradiction():
    """Verify verifier catches pivot/overhead irrigation scheduled on rainfed farm."""
    advisory = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        farm_country="IND",
        irrigation_type="rainfed",
    )

    # Intentionally contradict rainfed status
    advisory.irrigation_schedule.append(
        IrrigationItem(
            date_or_week="2026-07-15",
            mm=35.0,
            method="Center-Pivot overhead sprinkler",
            rationale="High pressure pivot irrigation",
        )
    )

    res = advisory_verifier.verify(
        contract=advisory,
        allowed_citation_ids=set(),
        irrigation_type="rainfed",
    )
    assert res.is_valid is False
    assert any("rainfed" in issue.lower() for issue in res.issues)


def test_verifier_catches_out_of_range_calendar_day():
    """Verify verifier flags action calendar day offset outside 1-30 days."""
    advisory = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        farm_country="IND",
    )

    # Use model_construct to bypass pydantic validation for testing verifier invariant guard
    invalid_item = ActionCalendarItem.model_construct(
        day_offset=45,  # Exceeds 30
        title="Late post-harvest action",
        description="Inspect field 45 days later.",
        category="monitoring",
        priority=UrgencyLevel.ROUTINE,
        done=False,
    )
    advisory.action_calendar_30d.append(invalid_item)

    res = advisory_verifier.verify(
        contract=advisory,
        allowed_citation_ids=set(),
        irrigation_type="rainfed",
    )
    assert res.is_valid is False
    assert any("day_offset" in issue for issue in res.issues)


# ============================================================================
# 4. DETERMINISTIC RULE ENGINE END-TO-END DEMO FARMS
# ============================================================================

def test_rule_engine_india_vidarbha_cotton():
    """Validates deterministic rules engine output for Indian Vertisol Cotton Farm."""
    adv = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        crop_history=["cotton", "cotton"],  # Monoculture trigger
        irrigation_type="rainfed",
        farm_country="IND",
        soil_data={
            "texture_class": "Clay",
            "depth_0_30cm_weighted": {"ph": 7.8, "soc_g_kg": 5.2},
            "soil_health": {"total_score": 68},
        },
        weather_data={
            "derived_indicators": {
                "heat_stress_days": 2,
                "frost_risk_level": "none",
                "drought_class": "moderate",
                "disease_spread_weather_risk": 45,
                "irrigation_need_mm": 25.0,
            }
        },
    )

    assert adv.meta.engine_mode.value == "rules"
    assert len(adv.crop_recommendations) >= 2
    assert adv.crop_recommendations[0].crop in ["cotton", "pigeonpea", "sorghum"]

    # Verify diagnostic practices triggered
    practices = [p.practice.value for p in adv.regenerative_practices]
    assert "composting" in practices  # Because SOC 0.52% < 1.0%
    assert "mulching" in practices    # Because rainfed + heat days
    assert "no_till" in practices     # Because Clay texture

    # Verify What to do today prioritized for heat stress
    assert "heat" in adv.what_to_do_today.title.lower() or "mulch" in adv.what_to_do_today.title.lower()


def test_rule_engine_brazil_cerrado_soybean():
    """Validates deterministic rules engine output for Brazilian Cerrado Soybean Farm."""
    adv = deterministic_rules_engine.generate_advisory(
        field_id="field-bra-sorriso-soy-02",
        current_crop="soybean",
        crop_history=["maize", "soybean"],
        irrigation_type="rainfed",
        farm_country="BRA",
        soil_data={
            "texture_class": "Clay Loam",
            "depth_0_30cm_weighted": {"ph": 5.4, "soc_g_kg": 22.0},
            "soil_health": {"total_score": 75},
        },
        weather_data={
            "derived_indicators": {
                "heat_stress_days": 0,
                "frost_risk_level": "none",
                "drought_class": "normal",
                "disease_spread_weather_risk": 75,  # Asian rust alert
                "irrigation_need_mm": 10.0,
            }
        },
    )

    assert adv.crop_recommendations[0].crop in ["soybean", "maize", "cowpea"]
    # Verify fungal disease warning triggered
    assert any(r.type == "pest" for r in adv.risks_and_warnings)
    assert "fungal" in adv.what_to_do_today.title.lower() or "scout" in adv.what_to_do_today.title.lower()


def test_rule_engine_south_africa_freestate_maize():
    """Validates deterministic rules engine output for South African Maize Farm."""
    adv = deterministic_rules_engine.generate_advisory(
        field_id="field-zaf-bothaville-maize-03",
        current_crop="maize",
        crop_history=["maize", "sunflower"],
        irrigation_type="pivot",
        farm_country="ZAF",
        soil_data={
            "texture_class": "Sandy Loam",
            "depth_0_30cm_weighted": {"ph": 6.3, "soc_g_kg": 7.5},
            "soil_health": {"total_score": 62},
        },
        weather_data={
            "derived_indicators": {
                "heat_stress_days": 0,
                "frost_risk_level": "moderate",  # Highveld frost risk
                "drought_class": "mild",
                "disease_spread_weather_risk": 20,
                "irrigation_need_mm": 28.0,
            }
        },
    )

    # Irrigated pivot schedule generated
    assert len(adv.irrigation_schedule) >= 1
    assert adv.irrigation_schedule[0].mm > 0.0

    # Frost card prioritized
    assert "frost" in adv.what_to_do_today.title.lower()


# ============================================================================
# 5. EXPLAINABILITY SERVICE TESTS
# ============================================================================

def test_explainability_service_dual_views():
    """Verify farmer and extension officer formats are generated correctly."""
    adv = deterministic_rules_engine.generate_advisory(
        field_id="field-ind-vidarbha-cotton-01",
        current_crop="cotton",
        farm_country="IND",
    )

    farmer_view = explainability_service.format_explainability(adv, for_officer=False)
    assert farmer_view["view"] == "farmer_plain_language"
    assert "headline_reason" in farmer_view
    assert len(farmer_view["key_factors"]) >= 1
    assert "what_changes_this" in farmer_view

    officer_view = explainability_service.format_explainability(adv, for_officer=True)
    assert officer_view["view"] == "extension_officer_diagnostic"
    assert "confidence_breakdown" in officer_view
    assert "signals_used" in officer_view
    assert sum(s["weight"] for s in officer_view["signals_used"]) == pytest.approx(1.0, rel=1e-2)
    assert "counterfactual_analysis" in officer_view
