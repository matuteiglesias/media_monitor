#!/usr/bin/env python3
"""Promote one news_article_draft.v1 row into a published_article.v1 bus record."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DRAFT_BUS = ROOT / "storage" / "buses" / "news_article_draft" / "v1"
PUBLISHED_BUS = ROOT / "storage" / "buses" / "published_article" / "v1"
SCHEMAS = ROOT / "contracts" / "schemas"

REQUIRED_DRAFT_FIELDS = [
    "schema_name",
    "draft_id",
    "digest_at",
    "story_group_id",
    "title",
    "summary",
    "body_md",
    "topic",
    "source_links",
    "citations",
    "status",
]


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{idx}: expected object row")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no JSONL rows")
    return rows


def find_draft_path(draft_id: str) -> Path:
    exact = DRAFT_BUS / f"{draft_id}.jsonl"
    if exact.exists():
        return exact
    matches: list[Path] = []
    for path in sorted(DRAFT_BUS.glob("*.jsonl")):
        if any(str(row.get("draft_id") or "") == draft_id for row in read_jsonl_rows(path)):
            matches.append(path)
    if not matches:
        raise FileNotFoundError(f"draft_id not found in {DRAFT_BUS}: {draft_id}")
    if len(matches) > 1:
        raise ValueError(f"draft_id found in multiple files: {', '.join(str(p) for p in matches)}")
    return matches[0]


def load_draft(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.draft_path) if args.draft_path else find_draft_path(args.draft_id)
    rows = read_jsonl_rows(path)
    if args.draft_id:
        rows = [row for row in rows if str(row.get("draft_id") or "") == args.draft_id]
    if len(rows) != 1:
        raise ValueError(f"expected exactly one draft row in {path}, got {len(rows)}")
    return rows[0]


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "article"


def stable_article_id(draft: dict[str, Any], slug: str) -> str:
    seed = f"{draft['digest_at']}|{draft['draft_id']}|{slug}"
    suffix = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"article_{suffix}"


def validate_draft(draft: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_DRAFT_FIELDS if not draft.get(field)]
    if missing:
        raise ValueError(f"draft missing required fields: {', '.join(missing)}")
    if draft.get("schema_name") != "news_article_draft.v1":
        raise ValueError(f"expected news_article_draft.v1, got {draft.get('schema_name')}")
    if draft.get("status") != "draft":
        raise ValueError(f"expected draft status, got {draft.get('status')}")
    if not isinstance(draft.get("source_links"), list) or not draft["source_links"]:
        raise ValueError("draft source_links must be a non-empty array")
    if not isinstance(draft.get("citations"), list):
        raise ValueError("draft citations must be an array")


def validate_published(article: dict[str, Any]) -> None:
    schema = json.loads((SCHEMAS / "published_article.v1.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(article), key=lambda e: list(e.path))
    if errors:
        raise ValueError("published article failed schema validation: " + "; ".join(e.message for e in errors))


def promote(draft: dict[str, Any], review_status: str) -> tuple[dict[str, Any], Path]:
    validate_draft(draft)
    slug = slugify(str(draft.get("slug_candidate") or draft["title"]))
    article_id = stable_article_id(draft, slug)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    article = {
        "schema_name": "published_article.v1",
        "article_id": article_id,
        "draft_id": draft["draft_id"],
        "digest_at": draft["digest_at"],
        "story_group_id": draft["story_group_id"],
        "slug": slug,
        "title": draft["title"],
        "summary": draft["summary"],
        "body_md": draft["body_md"],
        "topic": draft["topic"],
        "source_links": draft["source_links"],
        "citations": draft.get("citations") or [],
        "status": "published",
        "review_status": review_status,
        "published_at": now,
        "updated_at": now,
    }
    validate_published(article)
    PUBLISHED_BUS.mkdir(parents=True, exist_ok=True)
    out = PUBLISHED_BUS / f"{article_id}.jsonl"
    out.write_text(json.dumps(article, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return article, out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft-id")
    group.add_argument("--draft-path")
    parser.add_argument("--approve-human", action="store_true", help="Required explicit approval gate for publication")
    parser.add_argument("--review-status", default="human_approved")
    args = parser.parse_args()
    if not args.approve_human:
        raise SystemExit("refusing to publish without --approve-human")
    article, out = promote(load_draft(args), args.review_status)
    print(json.dumps({"status": "ok", "article_id": article["article_id"], "slug": article["slug"], "output_path": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
