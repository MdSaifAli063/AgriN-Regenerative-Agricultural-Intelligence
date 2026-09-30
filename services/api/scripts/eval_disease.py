#!/usr/bin/env python3
"""
KrishiNet-BRICS – Disease Diagnostic Evaluation Script.
scripts/eval_disease.py

Evaluates the Phase 5 ensemble diagnostic pipeline against a labelled test set,
reporting Accuracy, Weighted F1, Mean Confidence, and OOD rejection rate.

Usage:
    python scripts/eval_disease.py [--fixtures] [--csv PATH] [--threshold 0.42]

Options:
    --fixtures        Use built-in 30-label demo fixtures (no images needed).
    --csv PATH        CSV file with columns: image_path,true_label,crop_hint.
    --threshold FLOAT Confidence gate threshold (default: 0.42).
    --top-k INT       Top-K accuracy evaluation (default: 3).
    --output-json     Write results to eval_results.json.

Output:
    - Accuracy (top-1 and top-k)
    - Weighted F1 score
    - Per-class precision / recall
    - Mean ensemble confidence
    - OOD rejection rate
    - Below-threshold rate
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_SRC = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(_SRC))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./eval_demo.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
logger = logging.getLogger("krishinet.eval")

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EvalSample:
    true_label: str
    crop_hint: Optional[str]
    image_bytes: Optional[bytes]


@dataclass
class EvalResult:
    true_label: str
    predicted_label: str
    predicted_top_k: List[str]
    confidence: float
    confidence_sufficient: bool
    ood_rejected: bool
    fusion_strategy: str
    correct_top1: bool
    correct_topk: bool


@dataclass
class EvalSummary:
    total_samples: int
    top1_accuracy: float
    topk_accuracy: float
    top_k: int
    weighted_f1: float
    mean_confidence: float
    ood_rejection_rate: float
    below_threshold_rate: float
    per_class_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confusion_matrix_top5: Dict[str, Dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in demo fixtures (30 labels × 1 sample each)
# ---------------------------------------------------------------------------

# Minimal 1×1 valid JPEG
_DEMO_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
    b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
)

_DEMO_FIXTURES = [
    ("rice_blast", "rice"),
    ("wheat_rust_yellow", "wheat"),
    ("wheat_rust_stem", "wheat"),
    ("cotton_leaf_curl", "cotton"),
    ("cotton_fusarium_wilt", "cotton"),
    ("tomato_late_blight", "tomato"),
    ("tomato_early_blight", "tomato"),
    ("tomato_leaf_miner", "tomato"),
    ("maize_gray_leaf_spot", "maize"),
    ("maize_northern_blight", "maize"),
    ("soybean_sudden_death_syndrome", "soybean"),
    ("soybean_rust", "soybean"),
    ("potato_late_blight", "potato"),
    ("potato_early_blight", "potato"),
    ("groundnut_early_leaf_spot", "groundnut"),
    ("groundnut_late_leaf_spot", "groundnut"),
    ("sugarcane_red_rot", "sugarcane"),
    ("sugarcane_smut", "sugarcane"),
    ("chickpea_ascochyta_blight", "chickpea"),
    ("lentil_stemphylium_blight", "lentil"),
    ("mango_anthracnose", "mango"),
    ("banana_panama_wilt", "banana"),
    ("pearl_millet_downy_mildew", "pearl_millet"),
    ("chilli_anthracnose", "chilli"),
    ("onion_purple_blotch", "onion"),
    ("mustard_white_rust", "mustard"),
    ("sunflower_downy_mildew", "sunflower"),
    ("cassava_mosaic", "cassava"),
    ("tea_blister_blight", "tea"),
    ("healthy", "rice"),
]


def _load_demo_fixtures() -> List[EvalSample]:
    return [
        EvalSample(true_label=label, crop_hint=crop, image_bytes=_DEMO_JPEG)
        for label, crop in _DEMO_FIXTURES
    ]


def _load_csv_fixtures(csv_path: str) -> List[EvalSample]:
    """Loads evaluation samples from a CSV: image_path,true_label,crop_hint."""
    import csv
    samples = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_path = Path(row["image_path"])
            if img_path.exists():
                image_bytes = img_path.read_bytes()
            else:
                logger.warning(f"Image not found: {img_path}; using demo JPEG placeholder.")
                image_bytes = _DEMO_JPEG
            samples.append(
                EvalSample(
                    true_label=row["true_label"].strip(),
                    crop_hint=row.get("crop_hint", "").strip() or None,
                    image_bytes=image_bytes,
                )
            )
    return samples


# ---------------------------------------------------------------------------
# Inference runner
# ---------------------------------------------------------------------------

async def _run_inference(sample: EvalSample, top_k: int) -> EvalResult:
    """Runs the full ensemble pipeline on one sample."""
    from app.ml.edge_inference import run_edge_inference
    from app.ml.vision_client import run_gemini_vision
    from app.services.disease.ensemble import fuse_predictions
    from app.services.disease.report import build_diagnosis_report

    image_bytes = sample.image_bytes or _DEMO_JPEG

    # Parallel inference
    import asyncio
    edge_pred, gemini_pred = await asyncio.gather(
        asyncio.to_thread(run_edge_inference, image_bytes, True, top_k),
        run_gemini_vision(image_bytes, crop_hint=sample.crop_hint),
        return_exceptions=True,
    )

    if isinstance(edge_pred, Exception):
        edge_pred = None
    if isinstance(gemini_pred, Exception):
        gemini_pred = None

    ensemble = fuse_predictions(edge_pred, gemini_pred, crop_hint=sample.crop_hint)
    report = build_diagnosis_report(ensemble)

    predicted_label = report.primary_disease_label
    top_k_labels = [p.label for p in report.top_3_predictions[:top_k]]

    return EvalResult(
        true_label=sample.true_label,
        predicted_label=predicted_label,
        predicted_top_k=top_k_labels,
        confidence=report.ensemble_confidence,
        confidence_sufficient=report.confidence_sufficient,
        ood_rejected=report.ood_rejected,
        fusion_strategy=report.fusion_strategy,
        correct_top1=(predicted_label == sample.true_label),
        correct_topk=(sample.true_label in top_k_labels),
    )


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def _compute_metrics(results: List[EvalResult], top_k: int) -> EvalSummary:
    n = len(results)
    if n == 0:
        return EvalSummary(0, 0.0, 0.0, top_k, 0.0, 0.0, 0.0, 0.0)

    top1_correct = sum(1 for r in results if r.correct_top1)
    topk_correct = sum(1 for r in results if r.correct_topk)
    ood_rejected = sum(1 for r in results if r.ood_rejected)
    below_threshold = sum(1 for r in results if not r.confidence_sufficient)
    mean_conf = sum(r.confidence for r in results) / n

    # Per-class precision / recall
    class_tp: Dict[str, int] = defaultdict(int)
    class_fp: Dict[str, int] = defaultdict(int)
    class_fn: Dict[str, int] = defaultdict(int)
    class_support: Dict[str, int] = defaultdict(int)

    for r in results:
        class_support[r.true_label] += 1
        if r.correct_top1:
            class_tp[r.true_label] += 1
        else:
            class_fn[r.true_label] += 1
            class_fp[r.predicted_label] += 1

    per_class: Dict[str, Dict[str, float]] = {}
    total_weighted_f1 = 0.0

    for cls, support in class_support.items():
        tp = class_tp[cls]
        fp = class_fp[cls]
        fn = class_fn[cls]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        per_class[cls] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": support,
        }
        total_weighted_f1 += f1 * support

    weighted_f1 = total_weighted_f1 / n if n > 0 else 0.0

    # Confusion matrix (top-5 most common true labels)
    top_classes = sorted(class_support.keys(), key=lambda c: -class_support[c])[:5]
    confusion: Dict[str, Dict[str, int]] = {c: defaultdict(int) for c in top_classes}
    for r in results:
        if r.true_label in confusion:
            confusion[r.true_label][r.predicted_label] += 1

    return EvalSummary(
        total_samples=n,
        top1_accuracy=round(top1_correct / n, 4),
        topk_accuracy=round(topk_correct / n, 4),
        top_k=top_k,
        weighted_f1=round(weighted_f1, 4),
        mean_confidence=round(mean_conf, 4),
        ood_rejection_rate=round(ood_rejected / n, 4),
        below_threshold_rate=round(below_threshold / n, 4),
        per_class_metrics=per_class,
        confusion_matrix_top5={k: dict(v) for k, v in confusion.items()},
    )


def _print_summary(summary: EvalSummary, results: List[EvalResult]) -> None:
    print("\n" + "=" * 65)
    print("  KrishiNet-BRICS | Disease Diagnostic Evaluation Report")
    print("=" * 65)
    print(f"  Total samples evaluated : {summary.total_samples}")
    print(f"  Top-1 Accuracy          : {summary.top1_accuracy:.1%}")
    print(f"  Top-{summary.top_k} Accuracy          : {summary.topk_accuracy:.1%}")
    print(f"  Weighted F1             : {summary.weighted_f1:.4f}")
    print(f"  Mean Ensemble Confidence: {summary.mean_confidence:.1%}")
    print(f"  OOD Rejection Rate      : {summary.ood_rejection_rate:.1%}")
    print(f"  Below-Threshold Rate    : {summary.below_threshold_rate:.1%}")
    print()
    print("  Per-class Metrics (precision / recall / F1 / support):")
    print(f"  {'Class':<40} {'P':>6} {'R':>6} {'F1':>6} {'N':>5}")
    print("  " + "-" * 63)
    for cls, m in sorted(summary.per_class_metrics.items()):
        print(
            f"  {cls:<40} {m['precision']:>6.3f} {m['recall']:>6.3f} "
            f"{m['f1']:>6.3f} {m['support']:>5}"
        )
    print()
    if summary.confusion_matrix_top5:
        print("  Confusion Matrix (top-5 classes, true vs predicted):")
        for true_cls, pred_counts in summary.confusion_matrix_top5.items():
            top_preds = sorted(pred_counts.items(), key=lambda x: -x[1])[:3]
            pred_str = ", ".join(f"{p}({c})" for p, c in top_preds)
            print(f"    {true_cls:<35} → {pred_str}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    if args.fixtures:
        samples = _load_demo_fixtures()
        print(f"Loaded {len(samples)} demo fixture samples.")
    elif args.csv:
        samples = _load_csv_fixtures(args.csv)
        print(f"Loaded {len(samples)} samples from {args.csv}.")
    else:
        print("No input specified. Use --fixtures or --csv PATH.")
        print("Using --fixtures (demo mode) by default.")
        samples = _load_demo_fixtures()

    print(f"Running evaluation (top_k={args.top_k}, threshold={args.threshold})...")

    # Override confidence threshold if specified
    try:
        import app.services.disease.report as _report_mod
        _report_mod._DEFAULT_CONFIDENCE_THRESHOLD = args.threshold
    except Exception:
        pass

    results: List[EvalResult] = []
    for i, sample in enumerate(samples):
        try:
            result = await _run_inference(sample, top_k=args.top_k)
            results.append(result)
            status = "✓" if result.correct_top1 else "✗"
            print(
                f"  [{i+1:3d}/{len(samples)}] {status} "
                f"true={sample.true_label:<35} "
                f"pred={result.predicted_label:<35} "
                f"conf={result.confidence:.2f}"
            )
        except Exception as exc:
            logger.error(f"Inference failed for {sample.true_label}: {exc}")
            results.append(
                EvalResult(
                    true_label=sample.true_label,
                    predicted_label="error",
                    predicted_top_k=[],
                    confidence=0.0,
                    confidence_sufficient=False,
                    ood_rejected=False,
                    fusion_strategy="error",
                    correct_top1=False,
                    correct_topk=False,
                )
            )

    summary = _compute_metrics(results, top_k=args.top_k)
    _print_summary(summary, results)

    if args.output_json:
        out_path = Path("eval_results.json")
        out_path.write_text(
            json.dumps(asdict(summary), indent=2),
            encoding="utf-8",
        )
        print(f"\nResults written to {out_path.absolute()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="KrishiNet-BRICS Disease Diagnostic Evaluation Script"
    )
    parser.add_argument("--fixtures", action="store_true",
                        help="Use 30 built-in demo fixtures")
    parser.add_argument("--csv", type=str, default=None,
                        help="CSV file with image_path,true_label,crop_hint columns")
    parser.add_argument("--threshold", type=float, default=0.42,
                        help="Confidence gate threshold (default 0.42)")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Top-K accuracy (default 3)")
    parser.add_argument("--output-json", action="store_true",
                        help="Write results to eval_results.json")
    args = parser.parse_args()
    asyncio.run(main(args))
