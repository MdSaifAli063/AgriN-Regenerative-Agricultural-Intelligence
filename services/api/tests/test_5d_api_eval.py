"""
Part 5D Tests – API Router, Offline Sync, Schemas, and Eval Script.

Tests run fully offline using FastAPI TestClient with mocked services.
No database, MinIO, or Gemini key required.
DEMO_MODE is forced True via environment.
"""

from __future__ import annotations

import asyncio
import datetime
import io
import json
import types
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal JPEG bytes for upload tests
# ---------------------------------------------------------------------------

_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
    b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_report(
    disease_label: str = "rice_blast",
    disease_name: str = "Rice Blast",
    confidence: float = 0.80,
):
    """Creates a mock DiagnosisReport-like namespace."""
    from app.services.disease.report import DiagnosisReport, Top3Prediction
    return DiagnosisReport(
        primary_disease_name=disease_name,
        primary_disease_label=disease_label,
        canonical_name=disease_name,
        fao_agrovoc_uri="http://aims.fao.org/aos/agrovoc/c_25344",
        severity_level="moderate",
        spread_risk_score="moderate",
        top_3_predictions=[
            Top3Prediction(label=disease_label, confidence=confidence, canonical_name=disease_name),
            Top3Prediction(label="healthy", confidence=0.10, canonical_name=None),
        ],
        ensemble_confidence=confidence,
        organic_treatment="Apply neem-based biopesticide.",
        chemical_treatment=None,
        chemical_safety_warning=None,
        prevention_measures=["Use resistant varieties.", "Ensure proper drainage."],
        weather_risk_amplified=True,
        weather_risk_factors=["High humidity above 80%"],
        visual_reasoning="Diamond-shaped lesions detected.",
        is_healthy=False,
        confidence_sufficient=True,
        confidence_guard_threshold=0.42,
        fusion_strategy="weighted_sum",
        edge_weight=0.55,
        gemini_weight=0.45,
        ood_rejected=False,
        playbook_version="1.0.0",
        model_version="demo_v1",
    )


# ---------------------------------------------------------------------------
# Disease schema tests
# ---------------------------------------------------------------------------

class TestDiseaseSchemas:
    def test_diagnose_request_defaults(self):
        """DiagnoseRequest has sensible defaults."""
        from app.schemas.disease import DiagnoseRequest
        req = DiagnoseRequest()
        assert req.language == "en"
        assert req.latitude == 0.0
        assert req.longitude == 0.0
        assert req.field_id is None

    def test_offline_sync_uri_validator_rejects_bare_path(self):
        """OfflineSyncItem rejects non-URI image paths."""
        from app.schemas.disease import OfflineSyncItem
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="must begin with"):
            OfflineSyncItem(
                client_id=str(uuid.uuid4()),
                image_s3_uri="/local/path/image.jpg",
            )

    def test_offline_sync_uri_accepts_s3(self):
        """OfflineSyncItem accepts s3:// URIs."""
        from app.schemas.disease import OfflineSyncItem
        item = OfflineSyncItem(
            client_id=str(uuid.uuid4()),
            image_s3_uri="s3://my-bucket/img.jpg",
        )
        assert item.image_s3_uri.startswith("s3://")

    def test_offline_sync_request_max_50(self):
        """OfflineSyncRequest rejects more than 50 items."""
        from app.schemas.disease import OfflineSyncRequest, OfflineSyncItem
        from pydantic import ValidationError
        items = [
            OfflineSyncItem(client_id=str(uuid.uuid4()), image_s3_uri="s3://b/k.jpg")
            for _ in range(51)
        ]
        with pytest.raises(ValidationError):
            OfflineSyncRequest(items=items)

    def test_diagnose_response_serializable(self):
        """DiagnoseResponse serializes cleanly to JSON."""
        from app.schemas.disease import DiagnoseResponse, Top3PredictionOut
        resp = DiagnoseResponse(
            detection_id=str(uuid.uuid4()),
            primary_disease_name="Rice Blast",
            primary_disease_label="rice_blast",
            canonical_name="Rice Blast",
            fao_agrovoc_uri=None,
            severity_level="moderate",
            spread_risk_score="moderate",
            top_3_predictions=[
                Top3PredictionOut(label="rice_blast", confidence=0.80)
            ],
            ensemble_confidence=0.80,
            organic_treatment="Neem oil spray.",
            prevention_measures=["Drainage"],
            weather_risk_amplified=False,
            weather_risk_factors=[],
            visual_reasoning="Lesions detected.",
            is_healthy=False,
            confidence_sufficient=True,
            fusion_strategy="weighted_sum",
            edge_weight=0.55,
            gemini_weight=0.45,
            ood_rejected=False,
            model_version="demo_v1",
            image_s3_uri="s3://demo/image.jpg",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        j = resp.model_dump_json()
        data = json.loads(j)
        assert data["primary_disease_label"] == "rice_blast"
        assert data["ensemble_confidence"] == 0.80


# ---------------------------------------------------------------------------
# Aggregation + feed round-trip
# ---------------------------------------------------------------------------

class TestFeedRoundTrip:
    """Integration: aggregation → GeoJSON feed → validate all properties."""

    def _run_aggregation(self):
        import types, datetime
        from app.services.disease.aggregation import aggregate_detections

        UTC = datetime.timezone.utc
        now = datetime.datetime.now(UTC)
        detections = [
            types.SimpleNamespace(
                id=f"d_{i}", farmer_id=f"f_{i % 8}",
                primary_disease_name="Rice Blast",
                latitude=28.601 + i * 0.00001,
                longitude=77.201 + i * 0.00001,
                created_at=now,
            )
            for i in range(8)
        ]
        return aggregate_detections(
            detections, "IND",
            now - datetime.timedelta(hours=24), now,
        )

    def test_geojson_roundtrip(self):
        from app.services.disease.outbreak_feed import build_geojson_feed
        result = self._run_aggregation()
        if not result.aggregates:
            pytest.skip("No aggregates (k-anon suppressed); skipping feed roundtrip.")
        feed = build_geojson_feed(result.aggregates)
        assert feed["type"] == "FeatureCollection"
        for feature in feed["features"]:
            assert feature["geometry"]["type"] == "Point"
            lon, lat = feature["geometry"]["coordinates"]
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90

    def test_jsonld_roundtrip(self):
        from app.services.disease.outbreak_feed import build_jsonld_feed
        result = self._run_aggregation()
        if not result.aggregates:
            pytest.skip("No aggregates; skipping JSON-LD roundtrip.")
        feed = build_jsonld_feed(result.aggregates)
        assert feed["@type"] == "Dataset"
        for node in feed["@graph"]:
            assert node["@type"] == "Event"
            assert "location" in node


# ---------------------------------------------------------------------------
# Diagnostic service tuple return
# ---------------------------------------------------------------------------

class TestDiagnosticServiceTuple:
    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        """diagnose() must return (DiagnosisReport, str) tuple."""
        from app.services.disease.diagnostic_service import DiagnosticService
        from app.services.disease.report import DiagnosisReport

        svc = DiagnosticService()

        with patch("app.ml.preprocessing.load_and_orient_image") as mock_load:
            with patch("app.services.disease.diagnostic_service.check_image_quality") as mock_quality:
                with patch("app.services.disease.diagnostic_service.run_edge_inference") as mock_edge:
                    with patch("app.services.disease.diagnostic_service.run_gemini_vision") as mock_gemini:
                        mock_load.return_value = MagicMock()
                        mock_quality.return_value = types.SimpleNamespace(
                            is_acceptable=True, blur_score=150.0, brightness_score=120.0,
                            issues=[], retake_tips=[]
                        )
                        # run_edge_inference is called via asyncio.to_thread -> wrap as sync return
                        mock_edge.return_value = None
                        # run_gemini_vision is an async function; return a coroutine
                        async def _fake_gemini(*a, **kw):
                            return None
                        mock_gemini.side_effect = _fake_gemini

                        result = await svc.diagnose(
                            image_bytes=_JPEG,
                            farmer_id="test-farmer",
                            db=None,
                        )

        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 2
        report, detection_id = result
        assert isinstance(report, DiagnosisReport)
        assert isinstance(detection_id, str)
        assert len(detection_id) == 36  # UUID format


# ---------------------------------------------------------------------------
# Eval script smoke test (fixtures mode) – using runpy to avoid module name issue
# ---------------------------------------------------------------------------

def _load_eval_module(module_name: str):
    """Loads the eval_disease script as a module using runpy."""
    import runpy
    eval_path = (
        __import__("pathlib").Path(__file__).parents[1] / "scripts" / "eval_disease.py"
    )
    if not eval_path.exists():
        return None
    globs = runpy.run_path(str(eval_path), run_name=module_name)
    return types.SimpleNamespace(**globs)


class TestEvalScript:
    def test_demo_fixtures_count(self):
        """Eval script fixture list must have 30 entries."""
        mod = _load_eval_module("eval_disease")
        if mod is None:
            pytest.skip("eval_disease.py not found")
        assert len(mod._DEMO_FIXTURES) == 30, (
            f"Expected 30 demo fixtures, got {len(mod._DEMO_FIXTURES)}"
        )

    def test_metrics_computation_perfect(self):
        """compute_metrics on all-correct results returns 1.0 accuracy."""
        mod = _load_eval_module("eval_disease_2")
        if mod is None:
            pytest.skip("eval_disease.py not found")

        EvalResult = mod.EvalResult
        results = [
            EvalResult(
                true_label=f"disease_{i}",
                predicted_label=f"disease_{i}",
                predicted_top_k=[f"disease_{i}", "healthy"],
                confidence=0.85,
                confidence_sufficient=True,
                ood_rejected=False,
                fusion_strategy="weighted_sum",
                correct_top1=True,
                correct_topk=True,
            )
            for i in range(10)
        ]
        summary = mod._compute_metrics(results, top_k=3)
        assert summary.top1_accuracy == 1.0
        assert summary.topk_accuracy == 1.0
        assert summary.weighted_f1 == 1.0
        assert summary.ood_rejection_rate == 0.0

    def test_metrics_computation_all_wrong(self):
        """compute_metrics on all-incorrect returns 0.0 accuracy."""
        mod = _load_eval_module("eval_disease_3")
        if mod is None:
            pytest.skip("eval_disease.py not found")

        EvalResult = mod.EvalResult
        results = [
            EvalResult(
                true_label="rice_blast",
                predicted_label="wheat_rust_yellow",
                predicted_top_k=["wheat_rust_yellow", "healthy"],
                confidence=0.55,
                confidence_sufficient=True,
                ood_rejected=False,
                fusion_strategy="gemini_only",
                correct_top1=False,
                correct_topk=False,
            )
            for _ in range(5)
        ]
        summary = mod._compute_metrics(results, top_k=3)
        assert summary.top1_accuracy == 0.0
        assert summary.topk_accuracy == 0.0


# ---------------------------------------------------------------------------
# Storage service extension test
# ---------------------------------------------------------------------------

class TestStorageService:
    def test_put_object_demo_mode(self):
        """put_object returns s3:// URI in demo mode without MinIO."""
        import app.services.storage as storage_mod
        svc = storage_mod.StorageService.__new__(storage_mod.StorageService)
        svc.bucket = "test-bucket"
        svc.MINIO_BUCKET = "test-bucket"
        svc.client = None  # Simulate no MinIO connection

        uri = svc.put_object("test/key.jpg", io.BytesIO(b"data"), "image/jpeg", 4)
        assert uri.startswith("s3://")
        assert "test/key.jpg" in uri

    def test_get_object_bytes_raises_in_demo(self):
        """get_object_bytes raises FileNotFoundError in demo mode."""
        import app.services.storage as storage_mod
        svc = storage_mod.StorageService.__new__(storage_mod.StorageService)
        svc.bucket = "test-bucket"
        svc.MINIO_BUCKET = "test-bucket"
        svc.client = None

        with pytest.raises(FileNotFoundError, match="Demo mode"):
            svc.get_object_bytes("some/key.jpg")
