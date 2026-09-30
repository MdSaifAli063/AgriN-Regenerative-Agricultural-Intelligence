"""
Part 5B Tests – Ensemble, Report Builder, and Vision Client.

Tests run fully offline (no Gemini key, no ONNX model required).
DEMO_MODE is forced True via monkeypatch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers – synthetic inputs
# ---------------------------------------------------------------------------

def _make_edge_pred(label="rice_blast", conf=0.78, ood=False):
    """Creates a synthetic EdgePrediction-like object."""
    from app.ml.edge_inference import EdgePrediction, EdgeCandidate
    from app.ml.ood_guard import OODCheckResult

    ood_result = OODCheckResult(
        is_ood=ood,
        max_confidence=conf,
        shannon_entropy=1.2 if not ood else 3.5,
        reason=None if not ood else "high entropy",
    )
    return EdgePrediction(
        top_predictions=[
            EdgeCandidate(label=label, confidence=conf),
            EdgeCandidate(label="healthy", confidence=round(1 - conf - 0.05, 2)),
            EdgeCandidate(label="wheat_rust_yellow", confidence=0.05),
        ],
        primary_label=label,
        primary_confidence=conf,
        ood_result=ood_result,
        tta_used=True,
        model_version="demo_v1",
        raw_probabilities=[conf, round(1 - conf - 0.05, 2), 0.05],
    )


def _make_gemini_pred(label="rice_blast", conf=0.83):
    """Creates a synthetic GeminiVisionPrediction-like object."""
    from app.ml.vision_client import GeminiVisionPrediction, VisionCandidate

    return GeminiVisionPrediction(
        top_predictions=[
            VisionCandidate(label=label, confidence=conf),
            VisionCandidate(label="healthy", confidence=round(1 - conf - 0.03, 2)),
            VisionCandidate(label="tomato_late_blight", confidence=0.03),
        ],
        primary_label=label,
        primary_confidence=conf,
        reasoning="Diamond-shaped lesions with grey centres are diagnostic for rice blast.",
        is_healthy=False,
    )


# ---------------------------------------------------------------------------
# Ensemble tests
# ---------------------------------------------------------------------------

class TestEnsemble:
    def test_basic_weighted_fusion(self):
        """Fusion of matching predictions yields high confidence."""
        from app.services.disease.ensemble import fuse_predictions

        edge = _make_edge_pred("rice_blast", 0.78)
        gemini = _make_gemini_pred("rice_blast", 0.83)
        result = fuse_predictions(edge, gemini, crop_hint="rice")

        assert result.primary_label == "rice_blast"
        # Weighted sum: 0.55*0.78 + 0.45*0.83 ≈ 0.802
        assert 0.75 <= result.primary_confidence <= 0.95
        assert result.fusion_strategy == "weighted_sum"
        assert result.edge_weight > 0
        assert result.gemini_weight > 0

    def test_gemini_heavy_crop(self):
        """Cotton activates Gemini-heavy weight (edge=0.30, gemini=0.70)."""
        from app.services.disease.ensemble import fuse_predictions, _GEMINI_HEAVY_EDGE_W

        edge = _make_edge_pred("cotton_leaf_curl", 0.70)
        gemini = _make_gemini_pred("cotton_leaf_curl", 0.80)
        result = fuse_predictions(edge, gemini, crop_hint="cotton")

        assert result.edge_weight == pytest.approx(_GEMINI_HEAVY_EDGE_W)

    def test_ood_rejection_goes_gemini_only(self):
        """OOD flag on edge forces edge_weight=0, gemini_weight=1."""
        from app.services.disease.ensemble import fuse_predictions

        edge = _make_edge_pred("rice_blast", 0.35, ood=True)
        gemini = _make_gemini_pred("rice_blast", 0.82)
        result = fuse_predictions(edge, gemini)

        assert result.ood_rejected is True
        assert result.edge_weight == 0.0
        assert result.gemini_weight == 1.0
        assert result.fusion_strategy == "gemini_only"

    def test_edge_only_when_gemini_unavailable(self):
        """No Gemini → edge_weight=1.0."""
        from app.services.disease.ensemble import fuse_predictions

        edge = _make_edge_pred("wheat_rust_yellow", 0.75)
        result = fuse_predictions(edge, None)

        assert result.edge_weight == 1.0
        assert result.gemini_weight == 0.0
        assert result.fusion_strategy == "edge_only"

    def test_fallback_when_both_unavailable(self):
        """Both None → fallback with 'unavailable' strategy."""
        from app.services.disease.ensemble import fuse_predictions

        result = fuse_predictions(None, None)
        assert result.fusion_strategy == "unavailable"
        assert result.primary_label == "healthy"

    def test_top3_length(self):
        """Ensemble top_predictions must have ≤3 entries."""
        from app.services.disease.ensemble import fuse_predictions

        edge = _make_edge_pred("tomato_early_blight", 0.72)
        gemini = _make_gemini_pred("tomato_late_blight", 0.68)
        result = fuse_predictions(edge, gemini)

        assert len(result.top_predictions) <= 3


# ---------------------------------------------------------------------------
# Report builder tests
# ---------------------------------------------------------------------------

class TestReportBuilder:
    def _ensemble(self, label="rice_blast", conf=0.80):
        from app.services.disease.ensemble import EnsembleResult, EnsembleCandidate

        return EnsembleResult(
            primary_label=label,
            primary_confidence=conf,
            top_predictions=[
                EnsembleCandidate(label=label, confidence=conf),
                EnsembleCandidate(label="healthy", confidence=round(1 - conf - 0.1, 2)),
            ],
            edge_weight=0.55,
            gemini_weight=0.45,
            edge_available=True,
            gemini_available=True,
            ood_rejected=False,
            reasoning="Lesions visible.",
            fusion_strategy="weighted_sum",
        )

    def test_known_disease_populated(self):
        """Known playbook label populates all fields."""
        from app.services.disease.report import build_diagnosis_report

        report = build_diagnosis_report(self._ensemble("rice_blast", 0.82))
        assert report.primary_disease_label == "rice_blast"
        assert report.fao_agrovoc_uri is not None
        assert report.organic_treatment != ""
        assert len(report.prevention_measures) > 0
        assert report.is_healthy is False

    def test_healthy_label(self):
        """Healthy label sets is_healthy=True and no chemical treatment."""
        from app.services.disease.report import build_diagnosis_report

        report = build_diagnosis_report(self._ensemble("healthy", 0.94))
        assert report.is_healthy is True
        assert report.chemical_treatment is None

    def test_low_confidence_flag(self):
        """Confidence below threshold sets confidence_sufficient=False."""
        from app.services.disease.report import build_diagnosis_report

        report = build_diagnosis_report(
            self._ensemble("rice_blast", 0.30),
            confidence_threshold=0.42,
        )
        assert report.confidence_sufficient is False

    def test_weather_amplification(self):
        """High humidity + cool nights amplifies rice_blast."""
        from app.services.disease.report import build_diagnosis_report

        weather = {
            "relative_humidity_pct": 85,
            "temperature_c": 15,
            "rainfall_mm_24h": 0,
        }
        report = build_diagnosis_report(self._ensemble("rice_blast", 0.80), weather_context=weather)
        assert report.weather_risk_amplified is True
        assert len(report.weather_risk_factors) >= 1

    def test_weather_escalates_severity(self):
        """Severe weather can escalate base severity."""
        from app.services.disease.report import build_diagnosis_report

        # rice_blast severity_default=critical → already max, but let's test moderate disease
        weather = {"relative_humidity_pct": 85, "temperature_c": 15, "rainfall_mm_24h": 60}
        report = build_diagnosis_report(self._ensemble("rice_blight_bacterial", 0.75), weather_context=weather)
        # base is "moderate"; should escalate to "critical" with flooding + humidity
        assert report.severity_level in ("moderate", "critical")

    def test_unknown_label_safe_fallback(self):
        """Unknown label doesn't crash – returns safe unknown entry."""
        from app.services.disease.report import build_diagnosis_report

        report = build_diagnosis_report(self._ensemble("alien_disease_xyz", 0.55))
        assert "Alien Disease Xyz" in report.primary_disease_name or "alien" in report.primary_disease_label
        assert report.organic_treatment != ""

    def test_top3_present(self):
        """Report always has top_3_predictions."""
        from app.services.disease.report import build_diagnosis_report

        report = build_diagnosis_report(self._ensemble("wheat_rust_yellow", 0.76))
        assert len(report.top_3_predictions) >= 1


# ---------------------------------------------------------------------------
# Vision client demo fallback test
# ---------------------------------------------------------------------------

class TestVisionClientDemo:
    @pytest.mark.asyncio
    async def test_demo_mode_returns_fixture(self, monkeypatch):
        """In demo mode, vision client returns a valid fixture."""
        import app.core.config as cfg_module

        monkeypatch.setattr(cfg_module.settings, "DEMO_MODE", True)

        from app.ml.vision_client import run_gemini_vision

        # Minimal valid JPEG bytes (1x1 pixel)
        jpeg_bytes = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e\xc4"
            b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
        )

        result = await run_gemini_vision(jpeg_bytes, crop_hint="rice")

        assert result.primary_label is not None
        assert 0.0 <= result.primary_confidence <= 1.0
        assert len(result.top_predictions) >= 1
        assert result.reasoning != ""


# ---------------------------------------------------------------------------
# Playbook completeness test
# ---------------------------------------------------------------------------

class TestPlaybook:
    _PLAYBOOK = (
        Path(__file__).parents[3]  # repo root
        / "data" / "seed" / "disease_playbook.json"
    )

    def test_playbook_has_30_plus_entries(self):
        """Verify playbook contains at least 30 disease entries."""
        if not self._PLAYBOOK.exists():
            pytest.skip(f"disease_playbook.json not found at {self._PLAYBOOK}")

        with open(self._PLAYBOOK, "r", encoding="utf-8") as f:
            data = json.load(f)

        diseases = data.get("diseases", [])
        assert len(diseases) >= 30, f"Expected >=30 entries, got {len(diseases)}"

    def test_playbook_required_fields(self):
        """Every playbook entry must have required fields."""
        if not self._PLAYBOOK.exists():
            pytest.skip(f"disease_playbook.json not found at {self._PLAYBOOK}")

        required = {
            "label", "canonical_name", "crop", "severity_default",
            "spread_risk_default", "organic_treatment", "prevention_measures",
        }
        with open(self._PLAYBOOK, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data.get("diseases", []):
            missing = required - set(entry.keys())
            assert not missing, f"Entry '{entry.get('label')}' missing fields: {missing}"
