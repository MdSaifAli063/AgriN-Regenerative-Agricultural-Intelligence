"""
KrishiNet-BRICS – Diagnosis Ensemble Decision Engine.

Fuses edge (ONNX) + Gemini vision predictions into a single authoritative
diagnosis using dynamic weight assignment.

Weight strategy:
  - Default split: edge=0.55, gemini=0.45
  - Weak-coverage crops (cotton, cassava, banana, tea, coffee, sunflower):
    edge has limited training data → flip to edge=0.30, gemini=0.70
  - OOD flag from edge model: edge weight → 0.0 (Gemini-only)
  - Gemini unavailable (demo/no key): edge-only, weights edge=1.0

Ensemble algorithm:
  1. Build a unified label → probability dict from each source (weighted sum)
  2. Merge; argmax → primary_label
  3. Compute ensemble confidence = weighted_max_prob
  4. Re-rank top-3

Outputs EnsembleResult (used by report builder downstream).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.ml.edge_inference import EdgePrediction
from app.ml.vision_client import GeminiVisionPrediction

logger = logging.getLogger("krishinet.ml.ensemble")

# ---------------------------------------------------------------------------
# Crops where Gemini Vision gets a higher vote weight
# (sparse training data / highly visual / morphology-heavy)
# ---------------------------------------------------------------------------

_GEMINI_HEAVY_CROPS = frozenset({
    "cotton",
    "cassava",
    "banana",
    "tea",
    "coffee",
    "sunflower",
    "mango",
    "sugarcane",
})

# Default weights
_DEFAULT_EDGE_W = 0.55
_DEFAULT_GEMINI_W = 0.45

# Gemini-heavy weights
_GEMINI_HEAVY_EDGE_W = 0.30
_GEMINI_HEAVY_GEMINI_W = 0.70


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EnsembleCandidate:
    label: str
    confidence: float  # fused probability [0, 1]
    edge_confidence: Optional[float] = None
    gemini_confidence: Optional[float] = None


@dataclass
class EnsembleResult:
    primary_label: str
    primary_confidence: float
    top_predictions: List[EnsembleCandidate]
    edge_weight: float
    gemini_weight: float
    edge_available: bool
    gemini_available: bool
    ood_rejected: bool
    reasoning: str  # from Gemini vision if available, else templated
    fusion_strategy: str  # "weighted_sum" | "gemini_only" | "edge_only"


# ---------------------------------------------------------------------------
# Core fusion logic
# ---------------------------------------------------------------------------

def _get_weights(
    crop_hint: Optional[str],
    edge_ood_rejected: bool,
    edge_available: bool,
    gemini_available: bool,
) -> Tuple[float, float]:
    """
    Returns (edge_weight, gemini_weight) normalised to sum to 1.0.
    """
    if not edge_available or edge_ood_rejected:
        return 0.0, 1.0

    if not gemini_available:
        return 1.0, 0.0

    crop_lower = (crop_hint or "").lower().strip()
    if any(c in crop_lower for c in _GEMINI_HEAVY_CROPS):
        return _GEMINI_HEAVY_EDGE_W, _GEMINI_HEAVY_GEMINI_W

    return _DEFAULT_EDGE_W, _DEFAULT_GEMINI_W


def fuse_predictions(
    edge_pred: Optional[EdgePrediction],
    gemini_pred: Optional[GeminiVisionPrediction],
    crop_hint: Optional[str] = None,
) -> EnsembleResult:
    """
    Fuses edge ONNX and Gemini vision predictions into an ensemble diagnosis.

    Args:
        edge_pred: Result from run_edge_inference(); None if model unavailable.
        gemini_pred: Result from run_gemini_vision(); None if unavailable.
        crop_hint: Optional crop name string (e.g. "rice").

    Returns:
        EnsembleResult with primary diagnosis and ranked top-3.
    """
    edge_available = edge_pred is not None
    gemini_available = gemini_pred is not None
    edge_ood_rejected = edge_available and edge_pred.ood_result.is_ood

    if not edge_available and not gemini_available:
        logger.error("Both edge and Gemini predictions unavailable – returning fallback.")
        return _fallback_ensemble()

    edge_w, gemini_w = _get_weights(
        crop_hint=crop_hint,
        edge_ood_rejected=edge_ood_rejected,
        edge_available=edge_available,
        gemini_available=gemini_available,
    )

    # ── Build unified label probability map ───────────────────────────────
    label_probs: Dict[str, Dict[str, float]] = {}  # label -> {edge, gemini, fused}

    if edge_available and edge_w > 0:
        for c in edge_pred.top_predictions:
            label_probs.setdefault(c.label, {"edge": 0.0, "gemini": 0.0})
            label_probs[c.label]["edge"] = c.confidence

    if gemini_available and gemini_w > 0:
        for c in gemini_pred.top_predictions:
            label_probs.setdefault(c.label, {"edge": 0.0, "gemini": 0.0})
            label_probs[c.label]["gemini"] = c.confidence

    # Compute weighted sum
    fused: Dict[str, float] = {}
    edge_lookup: Dict[str, float] = {}
    gemini_lookup: Dict[str, float] = {}
    for label, scores in label_probs.items():
        e = scores.get("edge", 0.0)
        g = scores.get("gemini", 0.0)
        fused[label] = round(edge_w * e + gemini_w * g, 4)
        edge_lookup[label] = e
        gemini_lookup[label] = g

    # ── Sort and take top-3 ───────────────────────────────────────────────
    sorted_labels = sorted(fused, key=lambda l: fused[l], reverse=True)[:3]
    top_predictions = [
        EnsembleCandidate(
            label=lbl,
            confidence=fused[lbl],
            edge_confidence=edge_lookup.get(lbl),
            gemini_confidence=gemini_lookup.get(lbl),
        )
        for lbl in sorted_labels
    ]

    primary = top_predictions[0]

    # ── Reasoning: prefer Gemini's visual explanation ─────────────────────
    reasoning = (
        gemini_pred.reasoning
        if gemini_available and gemini_pred.reasoning
        else _template_reasoning(primary.label, primary.confidence)
    )

    # ── Fusion strategy label ─────────────────────────────────────────────
    if edge_w == 0.0:
        strategy = "gemini_only"
    elif gemini_w == 0.0:
        strategy = "edge_only"
    else:
        strategy = "weighted_sum"

    logger.info(
        "Ensemble decision",
        extra={
            "primary": primary.label,
            "confidence": primary.confidence,
            "edge_w": edge_w,
            "gemini_w": gemini_w,
            "ood_rejected": edge_ood_rejected,
            "strategy": strategy,
        },
    )

    return EnsembleResult(
        primary_label=primary.label,
        primary_confidence=primary.confidence,
        top_predictions=top_predictions,
        edge_weight=edge_w,
        gemini_weight=gemini_w,
        edge_available=edge_available,
        gemini_available=gemini_available,
        ood_rejected=edge_ood_rejected,
        reasoning=reasoning,
        fusion_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _template_reasoning(label: str, confidence: float) -> str:
    """Generates a conservative template reasoning when Gemini is offline."""
    pct = int(confidence * 100)
    readable = label.replace("_", " ").title()
    return (
        f"On-device model predicted {readable} with {pct}% confidence based on "
        f"learned visual patterns from training data."
    )


def _fallback_ensemble() -> EnsembleResult:
    """Emergency fallback when both sources are unavailable."""
    return EnsembleResult(
        primary_label="healthy",
        primary_confidence=0.0,
        top_predictions=[
            EnsembleCandidate(label="healthy", confidence=0.0)
        ],
        edge_weight=0.0,
        gemini_weight=0.0,
        edge_available=False,
        gemini_available=False,
        ood_rejected=False,
        reasoning="Diagnosis engines unavailable; unable to process image at this time.",
        fusion_strategy="unavailable",
    )
