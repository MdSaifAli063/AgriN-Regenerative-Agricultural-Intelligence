"""Disease diagnostic service package."""
from app.services.disease.ensemble import fuse_predictions, EnsembleResult
from app.services.disease.report import build_diagnosis_report, DiagnosisReport
from app.services.disease.diagnostic_service import DiagnosticService
from app.services.disease.aggregation import (
    aggregate_detections,
    AggregationResult,
    coarsen_to_h3,
    add_laplace_noise,
    classify_severity,
    detect_spikes,
    _synthetic_demo_detections,
)
from app.services.disease.outbreak_feed import build_geojson_feed, build_jsonld_feed

__all__ = [
    "fuse_predictions",
    "EnsembleResult",
    "build_diagnosis_report",
    "DiagnosisReport",
    "DiagnosticService",
    "aggregate_detections",
    "AggregationResult",
    "coarsen_to_h3",
    "add_laplace_noise",
    "classify_severity",
    "detect_spikes",
    "_synthetic_demo_detections",
    "build_geojson_feed",
    "build_jsonld_feed",
]
