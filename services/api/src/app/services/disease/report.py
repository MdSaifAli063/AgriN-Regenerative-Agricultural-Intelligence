"""
KrishiNet-BRICS – Disease Report Builder.

Merges the ensemble diagnosis with:
  - Disease playbook data (treatments, prevention, FAO AGROVOC URI)
  - Weather risk amplification (from Phase 3 weather service response)
  - Confidence guard (reject if confidence < threshold)
  - Provenance block for audit

Output: DiagnosisReport (Pydantic model, directly serialised into API response
        and persisted to disease_detections table).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.disease.ensemble import EnsembleResult

logger = logging.getLogger("krishinet.ml.report")

# ---------------------------------------------------------------------------
# Playbook loader (singleton, loaded once)
# ---------------------------------------------------------------------------

_PLAYBOOK_PATH_CANDIDATES = [
    Path("data/seed/disease_playbook.json"),
    Path("../../data/seed/disease_playbook.json"),              # from services/api/
    Path(__file__).parents[6] / "data" / "seed" / "disease_playbook.json",  # repo root
    Path(__file__).parents[5] / "data" / "seed" / "disease_playbook.json",
    Path(__file__).parents[4] / "data" / "seed" / "disease_playbook.json",
    Path("/app/data/seed/disease_playbook.json"),               # Docker
]

_playbook_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _load_playbook() -> Dict[str, Dict[str, Any]]:
    global _playbook_cache
    if _playbook_cache is not None:
        return _playbook_cache

    for path in _PLAYBOOK_PATH_CANDIDATES:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            _playbook_cache = {d["label"]: d for d in raw.get("diseases", [])}
            logger.info(f"Disease playbook loaded: {len(_playbook_cache)} entries from {path}")
            return _playbook_cache

    logger.warning("Disease playbook not found – using empty fallback.")
    _playbook_cache = {}
    return _playbook_cache


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------

class Top3Prediction(BaseModel):
    label: str
    confidence: float
    canonical_name: Optional[str] = None


class DiagnosisReport(BaseModel):
    """
    Complete disease diagnosis report.
    Maps 1:1 with the DiseaseDetection DB model and API response schema.
    """
    primary_disease_name: str
    primary_disease_label: str
    canonical_name: str
    fao_agrovoc_uri: Optional[str] = None

    severity_level: str = "moderate"            # none | mild | moderate | critical
    spread_risk_score: str = "low"              # none | low | moderate | high | severe

    top_3_predictions: List[Top3Prediction]
    ensemble_confidence: float

    organic_treatment: str
    chemical_treatment: Optional[str] = None
    chemical_safety_warning: Optional[str] = None
    prevention_measures: List[str] = Field(default_factory=list)

    weather_risk_amplified: bool = False
    weather_risk_factors: List[str] = Field(default_factory=list)

    visual_reasoning: str
    is_healthy: bool

    confidence_sufficient: bool       # False → API returns low-confidence warning
    confidence_guard_threshold: float

    fusion_strategy: str
    edge_weight: float
    gemini_weight: float
    ood_rejected: bool

    # Provenance
    playbook_version: str = "1.0.0"
    model_version: str = "demo_v1"


# ---------------------------------------------------------------------------
# Confidence guard
# ---------------------------------------------------------------------------

_DEFAULT_CONFIDENCE_THRESHOLD = 0.42  # below this the report is flagged


def _check_confidence(confidence: float, threshold: float) -> bool:
    return confidence >= threshold


# ---------------------------------------------------------------------------
# Weather risk amplification
# ---------------------------------------------------------------------------

def _evaluate_weather_risk(
    playbook_entry: Dict[str, Any],
    weather_context: Optional[Dict[str, Any]],
) -> tuple[bool, List[str]]:
    """
    Checks whether current weather conditions amplify disease risk.

    Args:
        playbook_entry: Single disease entry from playbook.
        weather_context: Dict from WeatherService (may have keys like
            'relative_humidity', 'temperature_c', 'rainfall_mm_24h', etc.)

    Returns:
        (amplified: bool, matched_factors: List[str])
    """
    amplifiers: List[str] = playbook_entry.get("weather_risk_amplifiers", [])
    if not amplifiers or not weather_context:
        return False, []

    rh = weather_context.get("relative_humidity_pct", 0)
    temp = weather_context.get("temperature_c", 20)
    rain = weather_context.get("rainfall_mm_24h", 0)
    wind = weather_context.get("wind_speed_kmh", 0)

    matched: List[str] = []

    for amp in amplifiers:
        amp_l = amp.lower()
        if "high_humidity" in amp_l and rh > 75:
            matched.append(f"High relative humidity ({rh:.0f}%)")
        if "cool_nights" in amp_l and temp < 18:
            matched.append(f"Cool night temperature ({temp:.1f}°C)")
        if "warm" in amp_l and temp > 28:
            matched.append(f"Warm temperature ({temp:.1f}°C)")
        if "flooding" in amp_l and rain > 50:
            matched.append(f"Heavy rainfall ({rain:.1f} mm/24 h)")
        if "fog" in amp_l and rh > 90:
            matched.append("Foggy/mist conditions (RH > 90%)")
        if "water_logging" in amp_l and rain > 40:
            matched.append(f"Waterlogging risk (rainfall {rain:.1f} mm/24 h)")
        if "dry_conditions" in amp_l and rh < 35:
            matched.append(f"Dry conditions (RH {rh:.0f}%)")
        if "drought_stress" in amp_l and rain < 5 and rh < 40:
            matched.append("Drought stress conditions")

    return len(matched) > 0, list(dict.fromkeys(matched))  # deduplicate


# ---------------------------------------------------------------------------
# Severity escalation via weather
# ---------------------------------------------------------------------------

_SEVERITY_RANK = {"none": 0, "mild": 1, "moderate": 2, "critical": 3}
_SEVERITY_NAMES = {v: k for k, v in _SEVERITY_RANK.items()}


def _escalate_severity(base: str, weather_amplified: bool) -> str:
    """Bumps severity by one level when weather risk is active."""
    rank = _SEVERITY_RANK.get(base, 2)
    if weather_amplified:
        rank = min(rank + 1, 3)
    return _SEVERITY_NAMES[rank]


def _escalate_spread_risk(base: str, weather_amplified: bool, matched_count: int) -> str:
    """Bumps spread risk when weather amplifiers fire."""
    rank_map = {"none": 0, "low": 1, "moderate": 2, "high": 3, "severe": 4}
    rev_map = {v: k for k, v in rank_map.items()}
    rank = rank_map.get(base, 1)
    if weather_amplified and matched_count >= 2:
        rank = min(rank + 1, 4)
    return rev_map[rank]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_diagnosis_report(
    ensemble: EnsembleResult,
    weather_context: Optional[Dict[str, Any]] = None,
    model_version: str = "demo_v1",
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
) -> DiagnosisReport:
    """
    Constructs a complete DiagnosisReport from the ensemble result.

    Args:
        ensemble: Output of fuse_predictions().
        weather_context: Optional weather dict from WeatherService.
        model_version: Version string of the ONNX model used.
        confidence_threshold: Minimum confidence to mark report as reliable.

    Returns:
        DiagnosisReport with all fields populated.
    """
    playbook = _load_playbook()
    label = ensemble.primary_label
    entry = playbook.get(label, _unknown_entry(label))

    # ── Weather risk ──────────────────────────────────────────────────────
    weather_amplified, weather_factors = _evaluate_weather_risk(entry, weather_context)

    # ── Severity / spread risk ────────────────────────────────────────────
    severity = _escalate_severity(entry.get("severity_default", "moderate"), weather_amplified)
    spread_risk = _escalate_spread_risk(
        entry.get("spread_risk_default", "low"),
        weather_amplified,
        len(weather_factors),
    )

    # ── Top-3 mapping ─────────────────────────────────────────────────────
    top3 = [
        Top3Prediction(
            label=c.label,
            confidence=c.confidence,
            canonical_name=playbook.get(c.label, {}).get("canonical_name"),
        )
        for c in ensemble.top_predictions
    ]

    # ── Confidence guard ──────────────────────────────────────────────────
    confidence_ok = _check_confidence(ensemble.primary_confidence, confidence_threshold)
    if not confidence_ok:
        logger.warning(
            f"Low confidence diagnosis: {label} @ {ensemble.primary_confidence:.2%} "
            f"(threshold: {confidence_threshold:.2%})"
        )

    report = DiagnosisReport(
        primary_disease_name=entry.get("canonical_name", label.replace("_", " ").title()),
        primary_disease_label=label,
        canonical_name=entry.get("canonical_name", label.replace("_", " ").title()),
        fao_agrovoc_uri=entry.get("fao_agrovoc_uri"),
        severity_level=severity,
        spread_risk_score=spread_risk,
        top_3_predictions=top3,
        ensemble_confidence=ensemble.primary_confidence,
        organic_treatment=entry.get("organic_treatment", "Consult a local agronomist."),
        chemical_treatment=entry.get("chemical_treatment"),
        chemical_safety_warning=entry.get("chemical_safety_warning"),
        prevention_measures=entry.get("prevention_measures", []),
        weather_risk_amplified=weather_amplified,
        weather_risk_factors=weather_factors,
        visual_reasoning=ensemble.reasoning,
        is_healthy=(label == "healthy"),
        confidence_sufficient=confidence_ok,
        confidence_guard_threshold=confidence_threshold,
        fusion_strategy=ensemble.fusion_strategy,
        edge_weight=ensemble.edge_weight,
        gemini_weight=ensemble.gemini_weight,
        ood_rejected=ensemble.ood_rejected,
        playbook_version="1.0.0",
        model_version=model_version,
    )

    logger.info(
        "Diagnosis report built",
        extra={
            "label": label,
            "severity": severity,
            "spread_risk": spread_risk,
            "weather_amplified": weather_amplified,
            "confidence_ok": confidence_ok,
        },
    )
    return report


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _unknown_entry(label: str) -> Dict[str, Any]:
    """Returns a safe default playbook entry for an unrecognised label."""
    return {
        "canonical_name": label.replace("_", " ").title(),
        "fao_agrovoc_uri": None,
        "severity_default": "moderate",
        "spread_risk_default": "moderate",
        "organic_treatment": "Consult a certified local agronomist for identification and treatment.",
        "chemical_treatment": None,
        "chemical_safety_warning": None,
        "prevention_measures": ["Contact your local agricultural extension officer."],
        "weather_risk_amplifiers": [],
    }
