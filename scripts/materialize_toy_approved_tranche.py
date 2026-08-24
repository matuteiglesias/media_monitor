#!/usr/bin/env python3
"""Materialize a toy human-approved tranche for downstream acceptance tests.

This deliberately exercises the real promotion/index code with review_status=human_approved,
but only inside an isolated output directory. It must never touch the production published bus
or be represented as a real public editorial decision.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import promote_draft_to_published as promote_module
from build_published_article_indexes import build_indexes
from rehearse_c3_editorial_tranche import (
    DEFAULT_CANDIDATES,
    DEFAULT_LEDGER,
    read_jsonl,
    load_json,
    validate_candidates,
    validate_ledger,
)

TOY_SCOPE = "SIMULATED_TOY_HUMAN_APPROVAL_NOT_PUBLICATION"


def materialize(
    candidates_path: Path = DEFAULT_CANDIDATES,
    ledger_path: Path = DEFAULT_LEDGER,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    candidates = read_jsonl(candidates_path)
    validate_candidates(candidates)
    reviews = validate_ledger(load_json(ledger_path), candidates)

    temporary = None
    if output_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="media-monitor-c3-toy-")
        output_dir = Path(temporary.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    toy_bus = output_dir / "published_article" / "v1"
    toy_indexes = output_dir / "indexes"

    original_bus = promote_module.PUBLISHED_BUS
    approved: list[dict[str, Any]] = []
    try:
        promote_module.PUBLISHED_BUS = toy_bus
        for candidate in candidates:
            review = reviews[str(candidate["draft_id"])]
            if review["decision"] != "SIMULATED_APPROVE":
                continue
            article, _ = promote_module.promote(candidate, "human_approved")
            if article.get("review_status") != "human_approved":
                raise AssertionError("toy promotion did not exercise human-approved path")
            approved.append(article)
    finally:
        promote_module.PUBLISHED_BUS = original_bus

    latest_path, count = build_indexes(toy_bus, toy_indexes)
    if count != len(approved):
        raise AssertionError("toy publication index count mismatch")
    if {a["draft_id"] for a in approved} != {"c3-cpi-july-2026", "c3-trade-july-2026"}:
        raise AssertionError("toy tranche must preserve differentiated editorial judgment")

    manifest = {
        "schema_name": "toy_approval_manifest.v1",
        "scope": TOY_SCOPE,
        "not_for_publication": True,
        "production_bus_touched": False,
        "candidate_count": len(candidates),
        "approved_count": len(approved),
        "held_or_revise_count": len(candidates) - len(approved),
        "published_index_path": str(latest_path),
        "articles": [
            {
                "draft_id": article["draft_id"],
                "article_id": article["article_id"],
                "slug": article["slug"],
                "review_status": article["review_status"],
            }
            for article in approved
        ],
    }
    (output_dir / "toy_approval_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if temporary is not None:
        temporary.cleanup()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = materialize(args.candidates, args.ledger, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
