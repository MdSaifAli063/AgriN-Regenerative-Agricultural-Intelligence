"""
KrishiNet-BRICS – ONNX Edge Inference Engine.

Loads the on-device MobileNetV3-Small ONNX model and runs synchronous
inference with optional Test-Time Augmentation (TTA) averaging.

Architecture:
  - Single module-level session loaded once at import time (lazy on first call)
  - TTA: 4 variants averaged → reduces variance on field photos
  - Returns EdgePrediction with top-3 labels + probabilities + TTA flag
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.ml.preprocessing import (
    load_and_orient_image,
    preprocess_for_onnx,
    generate_tta_variants,
)
from app.ml.ood_guard import evaluate_ood_guard, OODCheckResult

logger = logging.getLogger("krishinet.ml.edge")

# ---------------------------------------------------------------------------
# Path resolution – falls back gracefully when model is absent (demo mode)
# ---------------------------------------------------------------------------

_MODEL_DIR = Path(__file__).parent / "assets"

def _resolve_model_path() -> Optional[Path]:
    """Walk standard locations for the ONNX model file."""
    candidates = [
        _MODEL_DIR / "disease_model.onnx",
        Path("ml/models/demo_v1/disease_model.onnx"),
        Path("/models/disease_model.onnx"),  # Docker volume mount
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return None


def _resolve_labels_path() -> Optional[Path]:
    candidates = [
        _MODEL_DIR / "labels.json",
        Path("ml/models/demo_v1/labels.json"),
        Path("/models/labels.json"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return None


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class EdgeCandidate:
    label: str
    confidence: float


@dataclass
class EdgePrediction:
    top_predictions: List[EdgeCandidate]
    primary_label: str
    primary_confidence: float
    ood_result: OODCheckResult
    tta_used: bool = False
    model_version: str = "unknown"
    raw_probabilities: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Session singleton
# ---------------------------------------------------------------------------

class _ONNXSessionSingleton:
    """Lazy-loading, process-scoped ONNX Runtime session."""

    def __init__(self):
        self._session = None
        self._labels: List[str] = []
        self._model_version = "unknown"
        self._load_attempted = False

    def _load(self) -> bool:
        if self._load_attempted:
            return self._session is not None
        self._load_attempted = True

        model_path = _resolve_model_path()
        labels_path = _resolve_labels_path()

        if model_path is None or labels_path is None:
            logger.warning(
                "ONNX model or labels not found – edge inference disabled. "
                "Run `python ml/scripts/make_demo_model.py` to generate demo artifacts."
            )
            return False

        try:
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = int(os.environ.get("ONNX_THREADS", "2"))
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )

            with open(labels_path, "r", encoding="utf-8") as f:
                label_data = json.load(f)
            self._labels = label_data if isinstance(label_data, list) else label_data.get("labels", [])
            self._model_version = label_data.get("version", "demo_v1") if isinstance(label_data, dict) else "demo_v1"

            logger.info(
                f"ONNX session loaded: {model_path.name} "
                f"({len(self._labels)} classes, v{self._model_version})"
            )
            return True

        except Exception as exc:
            logger.error(f"Failed to load ONNX model: {exc}")
            self._session = None
            return False

    @property
    def is_available(self) -> bool:
        return self._load()

    @property
    def labels(self) -> List[str]:
        self._load()
        return self._labels

    @property
    def model_version(self) -> str:
        return self._model_version

    def run(self, tensor: np.ndarray) -> np.ndarray:
        """Runs a single forward pass. Returns raw logits (1, num_classes)."""
        if self._session is None:
            raise RuntimeError("ONNX session is not loaded.")
        input_name = self._session.get_inputs()[0].name
        outputs = self._session.run(None, {input_name: tensor})
        return outputs[0]


_session = _ONNXSessionSingleton()


# ---------------------------------------------------------------------------
# Softmax utility
# ---------------------------------------------------------------------------

def _softmax(logits: np.ndarray) -> np.ndarray:
    logits = logits - np.max(logits)
    exp_l = np.exp(logits)
    return exp_l / (exp_l.sum() + 1e-9)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_edge_inference(
    image_bytes: bytes,
    use_tta: bool = True,
    top_k: int = 3,
) -> Optional[EdgePrediction]:
    """
    Runs ONNX edge inference on raw image bytes.

    Args:
        image_bytes: Raw JPEG/PNG bytes.
        use_tta: Whether to enable 4-variant TTA averaging.
        top_k: Number of top predictions to return (max 3).

    Returns:
        EdgePrediction if model is available; None otherwise.
    """
    if not _session.is_available:
        return None  # caller falls back to Gemini-only path

    try:
        image = load_and_orient_image(image_bytes)
        labels = _session.labels

        if use_tta:
            variants = generate_tta_variants(image)
            logits_list = []
            for v in variants:
                logits = _session.run(v)
                logits_list.append(logits[0])
            avg_logits = np.mean(logits_list, axis=0)
            probs = _softmax(avg_logits)
        else:
            tensor = preprocess_for_onnx(image)
            logits = _session.run(tensor)[0]
            probs = _softmax(logits)

        probs_list = probs.tolist()
        ood = evaluate_ood_guard(probs_list)

        # Build top-k
        top_indices = np.argsort(probs)[::-1][:top_k]
        top_preds = [
            EdgeCandidate(
                label=labels[i] if i < len(labels) else f"class_{i}",
                confidence=round(float(probs[i]), 4),
            )
            for i in top_indices
        ]

        primary = top_preds[0]

        return EdgePrediction(
            top_predictions=top_preds,
            primary_label=primary.label,
            primary_confidence=primary.confidence,
            ood_result=ood,
            tta_used=use_tta,
            model_version=_session.model_version,
            raw_probabilities=probs_list,
        )

    except Exception as exc:
        logger.error(f"Edge inference failed: {exc}", exc_info=True)
        return None
