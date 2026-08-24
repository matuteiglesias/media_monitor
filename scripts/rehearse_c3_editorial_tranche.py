#!/usr/bin/env python3
"""Rehearse a small editorial tranche without granting real publication approval."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import promote_draft_to_published as promote_module
from build_published_article_indexes import build_indexes

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "artifacts/editorial_c3_rehearsal/candidates.jsonl"
DEFAULT_LEDGER = ROOT / "artifacts/editorial_c3_rehearsal/review_ledger.json"
DRAFT_SCHEMA = ROOT / "contracts/schemas/news_article_draft.v1.json"
ALLOWED_DECISIONS = {"SIMULATED_APPROVE", "SIMULATED_REVISE", "SIMULATED_HOLD"}
SIMULATED_REVIEW_STATUS = "simulated_human_judgment_not_publication_approval"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{path}: no candidate drafts")
    return rows


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def validate_candidates(candidates: list[dict[str, Any]]) -> None:
    schema = load_json(DRAFT_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    seen: set[str] = set()
    for candidate in candidates:
        errors = sorted(validator.iter_errors(candidate), key=lambda e: list(e.path))
        if errors:
            raise ValueError(
                f"draft {candidate.get('draft_id')}: schema validation failed: "
                + "; ".join(error.message for error in errors)
            )
        draft_id = str(candidate["draft_id"])
        if draft_id in seen:
            raise ValueError(f"duplicate draft_id: {draft_id}")
        seen.add(draft_id)


def validate_ledger(ledger: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if ledger.get("review_mode") != "SIMULATED_HUMAN_JUDGMENT":
        raise ValueError("review ledger must be explicitly simulated")
    reviews = ledger.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("review ledger must contain reviews")
    by_id: dict[str, dict[str, Any]] = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("review entries must be objects")
        draft_id = str(review.get("draft_id") or "")
        decision = str(review.get("decision") or "")
        if not draft_id or decision not in ALLOWED_DECISIONS:
            raise ValueError(f"invalid simulated review entry for {draft_id!r}")
        if draft_id in by_id:
            raise ValueError(f"duplicate review for {draft_id}")
        by_id[draft_id] = review
    candidate_ids = {str(row["draft_id"]) for row in candidates}
    if set(by_id) != candidate_ids:
        raise ValueError(
            f"review/candidate mismatch: reviews={sorted(by_id)} candidates={sorted(candidate_ids)}"
        )
    return by_id


def rehearse(
    candidates_path: Path = DEFAULT_CANDIDATES,
    ledger_path: Path = DEFAULT_LEDGER,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    candidates = read_jsonl(candidates_path)
    validate_candidates(candidates)
    ledger = load_json(ledger_path)
    reviews = validate_ledger(ledger, candidates)

    temporary = None
    if output_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="media-monitor-c3-")
        output_dir = Path(temporary.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    simulated_bus = output_dir / "simulated_published"
    simulated_indexes = output_dir / "indexes"

    original_bus = promote_module.PUBLISHED_BUS
    promoted: list[dict[str, Any]] = []
    try:
        promote_module.PUBLISHED_BUS = simulated_bus
        for candidate in candidates:
            review = reviews[str(candidate["draft_id"])]
            if review["decision"] != "SIMULATED_APPROVE":
                continue
            article, _ = promote_module.promote(candidate, SIMULATED_REVIEW_STATUS)
            if article["review_status"] == "human_approved":
                raise AssertionError("rehearsal must never manufacture human_approved")
            promoted.append(article)
    finally:
        promote_module.PUBLISHED_BUS = original_bus

    _, indexed_count = build_indexes(simulated_bus, simulated_indexes)
    if indexed_count != len(promoted):
        raise AssertionError("simulated publication index count mismatch")

    decisions = {
        decision: sum(1 for review in reviews.values() if review["decision"] == decision)
        for decision in sorted(ALLOWED_DECISIONS)
    }
    report = {
        "schema_name": "c3_editorial_rehearsal_report.v1",
        "status": "ready_for_real_human_gate",
        "candidate_count": len(candidates),
        "decision_counts": decisions,
        "simulated_promoted_count": len(promoted),
        "simulated_promoted": [
            {
                "draft_id": article["draft_id"],
                "article_id": article["article_id"],
                "slug": article["slug"],
                "review_status": article["review_status"],
            }
            for article in promoted
        ],
        "real_publication_performed": False,
        "production_bus_touched": False,
        "next_gate": "Explicit human approval is still required before any real published_article.v1 promotion.",
    }

    (output_dir / "rehearsal_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if temporary is not None:
        temporary.cleanup()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    report = rehearse(args.candidates, args.ledger, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
