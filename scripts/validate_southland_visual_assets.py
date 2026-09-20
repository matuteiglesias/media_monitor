#!/usr/bin/env python3
"""Validate the Southland visual registry and its local public asset files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "config/southland_visual_assets.v1.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT / "contracts/schemas/southland_visual_assets.v1.json",
    )
    parser.add_argument("--require-files", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry),
        key=lambda error: list(error.path),
    )
    if errors:
        raise SystemExit(
            "visual registry schema errors: "
            + "; ".join(error.message for error in errors)
        )

    ids: set[str] = set()
    paths: set[str] = set()
    pending: list[str] = []
    missing: list[str] = []
    ready = 0

    for asset in registry["assets"]:
        asset_id = asset["asset_id"]
        public_path = asset["public_path"]
        if asset_id in ids:
            raise SystemExit(f"duplicate asset_id: {asset_id}")
        if public_path in paths:
            raise SystemExit(f"duplicate public_path: {public_path}")
        ids.add(asset_id)
        paths.add(public_path)

        target = ROOT / "apps/news_site/public" / public_path.lstrip("/")
        if not target.is_file():
            missing.append(asset_id)
        if asset["identity_status"] == "pending_lineage":
            pending.append(asset_id)
        elif asset["status"] == "approved":
            ready += 1

    if args.require_files and missing:
        raise SystemExit("missing asset files: " + ", ".join(missing))
    if args.require_ready and pending:
        raise SystemExit("assets still pending identity lineage: " + ", ".join(pending))

    print(
        json.dumps(
            {
                "schema_name": "southland_visual_assets_validation.v1",
                "status": "ok",
                "asset_count": len(registry["assets"]),
                "ready_count": ready,
                "pending_lineage_count": len(pending),
                "missing_file_count": len(missing),
                "pending_lineage": pending,
                "missing_files": missing,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
