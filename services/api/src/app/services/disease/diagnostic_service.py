"""
KrishiNet-BRICS – Disease Diagnostic Orchestration Service.

End-to-end pipeline:
  1. Image quality gate (blur / darkness)
  2. Parallel: ONNX edge inference + Gemini vision
  3. OOD guard (embedded in edge prediction)
  4. Ensemble fusion (dynamic crop-aware weights)
  5. Playbook lookup + weather amplification
  6. DiagnosisReport construction
  7. Persistence to disease_detections table (async)

Entry point: DiagnosticService.diagnose()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.quality import check_image_quality, ImageQualityReport
from app.ml.edge_inference import run_edge_inference, EdgePrediction
from app.ml.vision_client import run_gemini_vision, GeminiVisionPrediction
from app.services.disease.ensemble import fuse_predictions, EnsembleResult
from app.services.disease.report import build_diagnosis_report, DiagnosisReport

logger = logging.getLogger("krishinet.services.disease")


# ---------------------------------------------------------------------------
# Orchestration service
# ---------------------------------------------------------------------------

class DiagnosticService:
    """
    Stateless orchestration service for disease diagnosis.
    Instantiate once per request or inject as dependency.
    """

    async def diagnose(
        self,
        image_bytes: bytes,
        farmer_id: str,
        field_id: Optional[str] = None,
        crop_hint: Optional[str] = None,
        latitude: float = 0.0,
        longitude: float = 0.0,
        image_s3_uri: str = "",
        weather_context: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        offline_client_id: Optional[str] = None,
    ) -> Tuple[DiagnosisReport, str]:
        """
        Runs the full disease diagnostic pipeline.

        Args:
            image_bytes:     Raw image bytes (JPEG/PNG).
            farmer_id:       Farmer UUID for audit logging.
            field_id:        Optional field UUID.
            crop_hint:       Crop name hint for better ensemble weighting.
            latitude:        GPS latitude of the detection.
            longitude:       GPS longitude of the detection.
            image_s3_uri:    MinIO/S3 URI where the original image is stored.
            weather_context: Optional weather dict from WeatherService.
            db:              Optional async DB session for persistence.

        Returns:
            Tuple[DiagnosisReport, str]  – report and the persisted detection_id.

        Raises:
            ValueError: If image quality gate fails (blurry / too dark).
        """

        # ── Step 1: Image quality gate ────────────────────────────────────
        from app.ml.preprocessing import load_and_orient_image as _load
        _img = _load(image_bytes)
        quality: ImageQualityReport = check_image_quality(_img)
        if not quality.is_acceptable:
            issues_str = ", ".join(quality.issues) if quality.issues else "unknown"
            logger.warning(
                f"Image quality rejected [{farmer_id}]: {issues_str}"
            )
            tips = " ".join(quality.retake_tips) if quality.retake_tips else "Please retake in good daylight with a steady hand."
            raise ValueError(f"Image quality insufficient: {issues_str}. {tips}")

        logger.info(
            f"Image quality OK [farmer={farmer_id}] "
            f"blur={quality.blur_score:.1f} brightness={quality.brightness_score:.1f}"
        )

        # ── Step 2: Parallel edge + vision inference ──────────────────────
        edge_pred: Optional[EdgePrediction]
        gemini_pred: Optional[GeminiVisionPrediction]

        edge_task = asyncio.to_thread(
            run_edge_inference, image_bytes, True, 3
        )
        gemini_task = run_gemini_vision(
            image_bytes=image_bytes,
            crop_hint=crop_hint,
            user_id=farmer_id,
        )

        edge_pred, gemini_pred = await asyncio.gather(
            edge_task, gemini_task, return_exceptions=True
        )

        # Coerce exceptions to None (graceful degradation)
        if isinstance(edge_pred, Exception):
            logger.warning(f"Edge inference raised exception: {edge_pred}")
            edge_pred = None

        if isinstance(gemini_pred, Exception):
            logger.warning(f"Gemini vision raised exception: {gemini_pred}")
            gemini_pred = None

        # ── Step 3 + 4: Ensemble fusion ───────────────────────────────────
        ensemble: EnsembleResult = fuse_predictions(
            edge_pred=edge_pred,
            gemini_pred=gemini_pred,
            crop_hint=crop_hint,
        )

        # ── Step 5 + 6: Build report ──────────────────────────────────────
        model_version = edge_pred.model_version if edge_pred else "gemini_only"
        report: DiagnosisReport = build_diagnosis_report(
            ensemble=ensemble,
            weather_context=weather_context,
            model_version=model_version,
        )

        # ── Step 7: Persist to DB ─────────────────────────────────────────
        detection_id = str(uuid.uuid4())
        if db is not None:
            detection_id = await self._persist_detection(
                db=db,
                report=report,
                farmer_id=farmer_id,
                field_id=field_id,
                image_s3_uri=image_s3_uri,
                latitude=latitude,
                longitude=longitude,
                edge_pred=edge_pred,
                gemini_pred=gemini_pred,
                ensemble=ensemble,
                offline_client_id=offline_client_id,
            )

        return report, detection_id

    # ------------------------------------------------------------------
    # Persistence helper
    # ------------------------------------------------------------------

    async def _persist_detection(
        self,
        db: AsyncSession,
        report: DiagnosisReport,
        farmer_id: str,
        field_id: Optional[str],
        image_s3_uri: str,
        latitude: float,
        longitude: float,
        edge_pred,
        gemini_pred,
        ensemble: EnsembleResult,
        offline_client_id: Optional[str] = None,
    ) -> str:
        """Persists a DiseaseDetection row to the database. Returns the detection id."""
        try:
            from app.models.disease import DiseaseDetection

            edge_json = None
            if edge_pred:
                edge_json = {
                    "primary_label": edge_pred.primary_label,
                    "primary_confidence": edge_pred.primary_confidence,
                    "top": [
                        {"label": c.label, "confidence": c.confidence}
                        for c in edge_pred.top_predictions
                    ],
                    "ood_rejected": edge_pred.ood_result.is_ood,
                    "tta_used": edge_pred.tta_used,
                    "model_version": edge_pred.model_version,
                }

            gemini_json = None
            if gemini_pred:
                gemini_json = {
                    "primary_label": gemini_pred.primary_label,
                    "primary_confidence": gemini_pred.primary_confidence,
                    "top": [
                        {"label": c.label, "confidence": c.confidence}
                        for c in gemini_pred.top_predictions
                    ],
                    "reasoning": gemini_pred.reasoning,
                }

            ensemble_json = {
                "primary_label": ensemble.primary_label,
                "primary_confidence": ensemble.primary_confidence,
                "top": [
                    {"label": c.label, "confidence": c.confidence}
                    for c in ensemble.top_predictions
                ],
                "edge_weight": ensemble.edge_weight,
                "gemini_weight": ensemble.gemini_weight,
                "strategy": ensemble.fusion_strategy,
                "ood_rejected": ensemble.ood_rejected,
            }

            detection_id = str(uuid.uuid4())
            detection = DiseaseDetection(
                id=detection_id,
                farmer_id=farmer_id,
                field_id=field_id,
                image_s3_uri=image_s3_uri,
                edge_prediction=edge_json,
                gemini_vision_prediction=gemini_json,
                ensemble_prediction=ensemble_json,
                primary_disease_name=report.primary_disease_name,
                fao_agrovoc_uri=report.fao_agrovoc_uri,
                severity_level=report.severity_level,
                organic_treatment=report.organic_treatment,
                chemical_treatment=report.chemical_treatment,
                chemical_safety_warning=report.chemical_safety_warning,
                prevention_measures=report.prevention_measures,
                spread_risk_score=report.spread_risk_score,
                ensemble_confidence=report.ensemble_confidence,
                latitude=latitude,
                longitude=longitude,
                offline_client_id=offline_client_id,
            )

            db.add(detection)
            await db.flush()  # get the ID without committing (caller commits)
            logger.info(f"DiseaseDetection persisted: id={detection.id}")
            return detection_id

        except Exception as exc:
            logger.error(f"Failed to persist DiseaseDetection: {exc}", exc_info=True)
            await db.rollback()
            return str(uuid.uuid4())  # Return ephemeral ID so the response still works


# Module-level singleton for dependency injection
diagnostic_service = DiagnosticService()
