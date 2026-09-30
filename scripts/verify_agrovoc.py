#!/usr/bin/env python3
"""
scripts/verify_agrovoc.py
=========================
Validates that all domain terms used in KrishiNet's codebase have a
corresponding FAO AGROVOC mapping entry.

Usage:
    python scripts/verify_agrovoc.py [--strict]

Options:
    --strict    Exit with code 1 if any term is missing an AGROVOC URI
                (useful as a CI gate).

Exit Codes:
    0 – all terms resolved (or --strict not set)
    1 – one or more terms missing AGROVOC URI (only when --strict is used)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
MAPPING_PATH = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"

# -------------------------------------------------------------------------
# Domain terms expected to be resolvable
# These mirror the crops, soil properties, pests, and practices used
# in disease_playbook.json, the STAC collections, and the advisory engine.
# -------------------------------------------------------------------------
EXPECTED_TERMS = {
    "crops": [
        "wheat", "rice", "maize", "soybean", "sorghum", "coffee",
        "sugarcane", "cotton", "potato", "tomato", "chickpea",
        "groundnut", "cassava", "millet", "barley",
    ],
    "soil_properties": [
        "organic_carbon", "ph", "nitrogen", "phosphorus", "potassium",
        "cation_exchange_capacity", "bulk_density", "clay", "loam",
        "sandy_soil", "soil_moisture",
    ],
    "pests_and_diseases": [
        "fall_armyworm", "stem_rust", "late_blight", "desert_locust",
        "rice_blast", "powdery_mildew", "downy_mildew", "aphids", "whiteflies",
    ],
    "regenerative_practices": [
        "crop_rotation", "cover_crops", "conservation_tillage", "agroforestry",
        "organic_fertilizer", "composting", "biological_control", "intercropping",
    ],
}


def load_mapping(path: Path) -> dict:
    if not path.exists():
        print(f"[ERROR] Mapping file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify(mapping: dict, strict: bool) -> bool:
    """
    Returns True if all expected terms are present and have a valid AGROVOC URI.
    """
    mappings = mapping.get("mappings", {})
    all_ok = True
    total = 0
    resolved = 0
    missing: list[str] = []
    missing_uri: list[str] = []

    print(f"\n{'='*65}")
    print(" KrishiNet AGROVOC Verification Report")
    print(f" Mapping file: {MAPPING_PATH}")
    print(f"{'='*65}")

    for category, terms in EXPECTED_TERMS.items():
        category_data = mappings.get(category, {})
        print(f"\n  [{category.upper()}]")

        for term in terms:
            total += 1
            entry = category_data.get(term)
            if entry is None:
                print(f"    ✗ MISSING key : {term}")
                missing.append(f"{category}/{term}")
                all_ok = False
                continue

            uri = entry.get("uri") or entry.get("agrovoc_id")
            agrovoc_id = entry.get("agrovoc_id", "")

            if not uri:
                print(f"    ✗ NO URI      : {term}  (agrovoc_id={agrovoc_id or 'none'})")
                missing_uri.append(f"{category}/{term}")
                all_ok = False
            else:
                resolved += 1
                labels = entry.get("pref_label", {})
                label_en = labels.get("en", term)
                print(f"    ✓ {term:<30} → {agrovoc_id:<12} \"{label_en}\"")

    print(f"\n{'='*65}")
    print(f"  Resolved : {resolved}/{total}")
    if missing:
        print(f"  Missing keys : {', '.join(missing)}")
    if missing_uri:
        print(f"  Missing URIs : {', '.join(missing_uri)}")

    if all_ok:
        print("  STATUS : ✓ ALL TERMS RESOLVED – mapping is complete.")
    else:
        print("  STATUS : ✗ INCOMPLETE – see above for missing entries.")
    print(f"{'='*65}\n")

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify FAO AGROVOC mappings for KrishiNet.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any term is missing.")
    args = parser.parse_args()

    mapping = load_mapping(MAPPING_PATH)
    ok = verify(mapping, strict=args.strict)

    if not ok and args.strict:
        print("[STRICT MODE] Verification failed. Exiting with code 1.", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
