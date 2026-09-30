#!/usr/bin/env python3
"""
scripts/export_openapi.py
=========================
Exports the KrishiNet-BRICS FastAPI application's OpenAPI 3.1 schema to JSON
and Markdown summary.  Also validates mandatory interoperability endpoints.

Usage:
    python scripts/export_openapi.py [--output-dir docs] [--format json|yaml|both]

Outputs:
    docs/openapi.json          – Full OpenAPI 3.1 JSON schema
    docs/openapi_summary.md    – Human-readable endpoint summary table
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add the services/api/src directory to PYTHONPATH
REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "src"))

# Patch settings for export (avoid requiring live DB or env vars)
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./krishinet_dev.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("SECRET_KEY", "export-mode-placeholder-key")
os.environ.setdefault("NODE_ID", "IND-EXPORT")
os.environ.setdefault("NODE_COUNTRY", "IND")


MANDATORY_PATHS = {
    # OGC STAC 1.0.0
    "/stac": ["get"],
    "/stac/collections": ["get"],
    "/stac/search": ["get", "post"],
    # JSON-LD contexts
    "/contexts": ["get"],
    "/contexts/{context_file}": ["get"],
    # Node Passport
    "/.well-known/agrin-node.json": ["get"],
    # Federation
    "/api/v1/federation/agreements": ["get", "post"],
    "/api/v1/federation/egress/report": ["get"],
    "/api/v1/federation/egress/dry-run": ["post"],
}


def export_schema(output_dir: Path, fmt: str) -> dict:
    from app.main import create_app

    app = create_app()
    schema: dict = app.openapi()

    output_dir.mkdir(parents=True, exist_ok=True)

    if fmt in ("json", "both"):
        out_path = output_dir / "openapi.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        print(f"[✓] Exported JSON schema → {out_path}")

    if fmt in ("yaml", "both"):
        try:
            import yaml
            out_path = output_dir / "openapi.yaml"
            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
            print(f"[✓] Exported YAML schema → {out_path}")
        except ImportError:
            print("[!] PyYAML not installed; skipping YAML export. pip install pyyaml")

    return schema


def validate_mandatory_paths(schema: dict) -> bool:
    paths = schema.get("paths", {})
    all_ok = True
    print("\n  Mandatory Interoperability Path Validation:")
    for path, methods in MANDATORY_PATHS.items():
        path_obj = paths.get(path, {})
        for method in methods:
            if method in path_obj:
                print(f"    ✓ {method.upper():6s} {path}")
            else:
                print(f"    ✗ {method.upper():6s} {path}  ← MISSING")
                all_ok = False
    return all_ok


def generate_summary(schema: dict, output_dir: Path) -> None:
    paths = schema.get("paths", {})
    info = schema.get("info", {})
    title = info.get("title", "KrishiNet API")
    version = info.get("version", "unknown")

    lines = [
        f"# {title} – OpenAPI Summary",
        f"\n**Version**: `{version}`  \n**Standard**: OpenAPI 3.1.0\n",
        "## Endpoints\n",
        "| Method | Path | Tags | Summary |",
        "|--------|------|------|---------|",
    ]

    for path, path_obj in sorted(paths.items()):
        for method, op in path_obj.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            tags = ", ".join(op.get("tags", []))
            summary = op.get("summary", "—")
            lines.append(f"| `{method.upper()}` | `{path}` | {tags} | {summary} |")

    summary_path = output_dir / "openapi_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[✓] Markdown summary → {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export KrishiNet OpenAPI 3.1 schema.")
    parser.add_argument("--output-dir", default="docs", help="Output directory (default: docs/)")
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "both"],
        default="json",
        help="Export format (default: json)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate mandatory interoperability paths (default: True)",
    )
    args = parser.parse_args()

    output_dir = REPO_ROOT / args.output_dir
    schema = export_schema(output_dir, args.format)

    if args.validate:
        ok = validate_mandatory_paths(schema)
        if not ok:
            print("\n[!] Some mandatory interoperability paths are missing from the schema.")
            sys.exit(1)

    generate_summary(schema, output_dir)
    print("\n[✓] OpenAPI export complete.\n")


if __name__ == "__main__":
    main()
