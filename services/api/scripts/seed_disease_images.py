#!/usr/bin/env python3
"""
KrishiNet-BRICS – Demo Disease Image Seeder.

Generates a set of realistic demo leaf images for each disease in the
disease_playbook.json, uploads them to MinIO (or writes locally in demo mode),
and seeds the database with DiseaseDetection records for the 3 demo farmers.

Usage:
    python scripts/seed_disease_images.py [--demo-only] [--count N]

Options:
    --demo-only   Skip MinIO and write images to data/seed/demo_images/ locally.
    --count N     Number of detections to seed per disease (default: 2).
    --dry-run     Print what would be seeded without writing anything.

Environment:
    Reads DATABASE_URL, REDIS_URL, MINIO_* from .env or environment.
    Set DEMO_MODE=true to use demo fixtures (no Gemini/ONNX required).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parents[1]
_SRC = _ROOT / "src"
sys.path.insert(0, str(_SRC))

# Ensure DEMO_MODE is set before importing app modules
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./demo.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("krishinet.seeder.disease")

# ---------------------------------------------------------------------------
# Minimal 1×1 placeholder JPEG (used when Pillow not available)
# ---------------------------------------------------------------------------
_PLACEHOLDER_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
    b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xd9"
)

# Demo farm / farmer IDs (must match Alembic seed data)
_DEMO_FARMERS = [
    {"id": "demo-farmer-001", "name": "Ravi Kumar (India)", "country_iso": "IND",
     "lat": 28.6139, "lon": 77.2090, "crop": "wheat"},
    {"id": "demo-farmer-002", "name": "Li Wei (China)", "country_iso": "CHN",
     "lat": 31.2304, "lon": 121.4737, "crop": "rice"},
    {"id": "demo-farmer-003", "name": "João Silva (Brazil)", "country_iso": "BRA",
     "lat": -15.7801, "lon": -47.9292, "crop": "soybean"},
]

# Subset of diseases to seed for demo (one per major crop)
_SEED_DISEASES = [
    "rice_blast",
    "wheat_rust_yellow",
    "cotton_leaf_curl",
    "tomato_late_blight",
    "maize_gray_leaf_spot",
    "soybean_sudden_death_syndrome",
    "healthy",
]


def _generate_demo_image(disease_label: str, size: int = 224) -> bytes:
    """
    Generates a synthetic leaf image as JPEG bytes.
    Uses Pillow if available; falls back to the 1×1 placeholder.
    Colors are keyed by disease category for visual distinctiveness.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import random

        _DISEASE_COLORS = {
            "blast": (139, 90, 43),
            "rust": (180, 120, 40),
            "blight": (80, 120, 40),
            "curl": (60, 100, 160),
            "spot": (100, 60, 120),
            "healthy": (34, 139, 34),
            "wilt": (160, 100, 50),
            "rot": (120, 60, 60),
        }

        # Pick color based on disease type keyword
        color = (34, 100, 34)  # default: leaf green
        for keyword, c in _DISEASE_COLORS.items():
            if keyword in disease_label:
                color = c
                break

        rng = random.Random(hash(disease_label) & 0xFFFF)

        img = Image.new("RGB", (size, size), color=(20, 80, 20))
        draw = ImageDraw.Draw(img)

        # Draw leaf-like ellipse
        r, g, b = color
        draw.ellipse(
            [(size // 8, size // 6), (7 * size // 8, 5 * size // 6)],
            fill=(r, g, b, 220),
        )

        # Add disease lesion patches
        if disease_label != "healthy":
            for _ in range(rng.randint(3, 8)):
                x = rng.randint(size // 4, 3 * size // 4)
                y = rng.randint(size // 4, 3 * size // 4)
                radius = rng.randint(8, 24)
                lesion_color = (
                    min(255, r + 60),
                    max(0, g - 40),
                    max(0, b - 20),
                )
                draw.ellipse(
                    [(x - radius, y - radius), (x + radius, y + radius)],
                    fill=lesion_color,
                )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    except ImportError:
        logger.debug("Pillow not available; using 1×1 placeholder JPEG.")
        return _PLACEHOLDER_JPEG


async def _seed_to_db(
    detections: List[Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """Inserts DiseaseDetection rows into the database."""
    if dry_run:
        logger.info(f"[DRY RUN] Would insert {len(detections)} detection rows.")
        return len(detections)

    try:
        from app.db.session import AsyncSessionLocal
        from app.models.disease import DiseaseDetection

        inserted = 0
        async with AsyncSessionLocal() as session:
            for det in detections:
                row = DiseaseDetection(**det)
                session.add(row)
                inserted += 1
            await session.commit()
        return inserted
    except Exception as exc:
        logger.warning(f"DB seeding skipped (no DB available): {exc}")
        return 0


def _save_image_locally(image_bytes: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image_bytes)
    logger.debug(f"  Saved image: {path}")


def _load_playbook() -> List[Dict[str, Any]]:
    """Loads the disease playbook JSON."""
    candidates = [
        _ROOT.parent.parent / "data" / "seed" / "disease_playbook.json",
        Path(__file__).resolve().parents[3] / "data" / "seed" / "disease_playbook.json" if len(Path(__file__).resolve().parents) > 3 else Path("data/seed/disease_playbook.json"),
        Path("data/seed/disease_playbook.json"),
        Path("../../data/seed/disease_playbook.json"),
        Path("/app/data/seed/disease_playbook.json"),
    ]
    for c in candidates:
        try:
            if c.exists():
                with open(c, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded playbook from {c}")
                return data.get("diseases", [])
        except Exception:
            continue
    logger.warning("disease_playbook.json not found; using _SEED_DISEASES labels only.")
    return [{"label": lbl, "canonical_name": lbl.replace("_", " ").title(),
             "severity_default": "moderate", "spread_risk_default": "moderate",
             "organic_treatment": "Consult extension officer.",
             "prevention_measures": ["Practice crop rotation."]}
            for lbl in _SEED_DISEASES]


async def main(args: argparse.Namespace) -> None:
    logger.info("=" * 60)
    logger.info("KrishiNet-BRICS Disease Demo Image Seeder")
    logger.info(f"  Count per disease:  {args.count}")
    logger.info(f"  Demo-only (no DB):  {args.demo_only}")
    logger.info(f"  Dry run:            {args.dry_run}")
    logger.info("=" * 60)

    playbook = _load_playbook()
    seed_labels = set(_SEED_DISEASES)
    diseases_to_seed = [d for d in playbook if d["label"] in seed_labels]
    if not diseases_to_seed:
        diseases_to_seed = playbook[:7]  # fallback: first 7

    image_dir = _ROOT.parent.parent / "data" / "seed" / "demo_images"
    detections: List[Dict[str, Any]] = []

    for disease in diseases_to_seed:
        label = disease["label"]
        canonical = disease.get("canonical_name", label.replace("_", " ").title())
        severity = disease.get("severity_default", "moderate")
        spread = disease.get("spread_risk_default", "moderate")
        organic_tx = disease.get("organic_treatment", "Consult extension officer.")
        prevention = disease.get("prevention_measures", [])

        logger.info(f"\nSeeding: {label} ({canonical})")

        for i in range(args.count):
            farmer = _DEMO_FARMERS[i % len(_DEMO_FARMERS)]
            image_bytes = _generate_demo_image(label, size=224)
            image_filename = f"{label}_{i:02d}_{farmer['id']}.jpg"

            if args.demo_only or args.dry_run:
                _save_image_locally(image_bytes, image_dir / image_filename)
                s3_uri = f"s3://krishinet-demo/demo_images/{image_filename}"
            else:
                # Upload to MinIO
                try:
                    from app.services.storage import storage_service
                    obj_key = f"demo_images/{image_filename}"
                    s3_uri = storage_service.put_object(
                        key=obj_key,
                        data=io.BytesIO(image_bytes),
                        content_type="image/jpeg",
                        length=len(image_bytes),
                    )
                    logger.debug(f"  Uploaded to MinIO: {s3_uri}")
                except Exception as e:
                    logger.warning(f"  MinIO upload failed ({e}); saving locally.")
                    _save_image_locally(image_bytes, image_dir / image_filename)
                    s3_uri = f"s3://krishinet-demo/demo_images/{image_filename}"

            logger.info(f"  [{i+1}/{args.count}] farmer={farmer['id']} → {s3_uri}")

            if not args.dry_run:
                detections.append({
                    "id": str(uuid.uuid4()),
                    "farmer_id": farmer["id"],
                    "field_id": None,
                    "image_s3_uri": s3_uri,
                    "edge_prediction": {"primary_label": label, "primary_confidence": 0.75,
                                        "top": [{"label": label, "confidence": 0.75}],
                                        "ood_rejected": False, "tta_used": True,
                                        "model_version": "demo_v1"},
                    "gemini_vision_prediction": {"primary_label": label, "primary_confidence": 0.82,
                                                 "top": [{"label": label, "confidence": 0.82}],
                                                 "reasoning": f"Demo: {canonical} detected."},
                    "ensemble_prediction": {"primary_label": label, "primary_confidence": 0.78,
                                           "top": [{"label": label, "confidence": 0.78}],
                                           "edge_weight": 0.55, "gemini_weight": 0.45,
                                           "strategy": "weighted_sum", "ood_rejected": False},
                    "primary_disease_name": canonical,
                    "fao_agrovoc_uri": disease.get("fao_agrovoc_uri"),
                    "severity_level": severity,
                    "organic_treatment": organic_tx,
                    "chemical_treatment": disease.get("chemical_treatment"),
                    "chemical_safety_warning": disease.get("chemical_safety_warning"),
                    "prevention_measures": prevention,
                    "spread_risk_score": spread,
                    "ensemble_confidence": 0.78,
                    "latitude": farmer["lat"] + i * 0.001,
                    "longitude": farmer["lon"] + i * 0.001,
                    "offline_client_id": None,
                })

    if not args.demo_only:
        inserted = await _seed_to_db(detections, dry_run=args.dry_run)
        logger.info(f"\n✅ Seeded {inserted} DiseaseDetection rows to database.")
    else:
        logger.info(f"\n✅ Images saved to {image_dir}")

    logger.info("Demo disease seeding complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KrishiNet-BRICS disease demo seeder")
    parser.add_argument("--demo-only", action="store_true",
                        help="Write images locally, skip DB seeding")
    parser.add_argument("--count", type=int, default=2,
                        help="Detections per disease (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing anything")
    args = parser.parse_args()
    asyncio.run(main(args))
