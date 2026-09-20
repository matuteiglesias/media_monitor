#!/usr/bin/env python3
"""Materialize accepted Southland AI drafts as a LOCAL-ONLY website preview.

This does not mutate the governed published_article bus and does not represent
human approval. It overlays accepted news_article_draft.v1 rows onto the
materialized Next app snapshot and marks the presentation as an unpublished
prepared-issue preview.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_site_snapshot import canonical_id, validate_schema
from compile_outlet import compile_outlet
from materialize_outlet_site import materialize
from outlet_runtime import resolve_outlet_runtime
from promote_draft_to_published import (
    slugify,
    stable_article_id,
    validate_draft,
    validate_published,
)

CONFIRM = "PREVIEW_UNPUBLISHED_DRAFTS"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_one_jsonl(path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError(f"{path}: expected exactly one JSON object row")
    return rows[0]


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def resolve_draft_path(root: Path, storage_dir: Path, value: str) -> Path:
    raw = Path(value)
    draft_bus = (storage_dir / "buses/news_article_draft/v1").resolve()
    # Prepared artifacts may be downloaded onto a different machine. The report
    # can therefore contain an absolute GitHub-runner path that is no longer
    # valid locally. The stable draft filename remains sufficient inside the
    # isolated draft bus.
    candidates = (
        [raw, draft_bus / raw.name]
        if raw.is_absolute()
        else [root / raw, storage_dir / raw, draft_bus / raw.name]
    )

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            try:
                resolved.relative_to(draft_bus)
            except ValueError as exc:
                raise ValueError(
                    f"prepared draft escapes isolated Southland draft bus: {resolved}"
                ) from exc
            return resolved
    raise FileNotFoundError(f"prepared draft does not exist: {value}")


def preview_article(draft: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
    validate_draft(draft)
    slug = slugify(str(draft.get("slug_candidate") or draft["title"]))
    article_id = stable_article_id(draft, slug)
    created_at = str(draft.get("created_at") or "").strip()
    if not created_at:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    article = {
        "schema_name": "published_article.v1",
        "article_id": f"preview_{ordinal:02d}_{article_id}",
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
        "review_status": "ai_preview_unapproved",
        "published_at": created_at,
        "updated_at": created_at,
    }
    validate_published(article)
    return article


def publication_ref(article: dict[str, Any]) -> dict[str, Any]:
    return {
        key: article[key]
        for key in (
            "article_id",
            "slug",
            "title",
            "summary",
            "topic",
            "published_at",
            "updated_at",
        )
    }


def materialize_preview(
    *,
    repo_root: Path,
    site_id: str,
    report_path: Path | None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    runtime = resolve_outlet_runtime(root, site_id)
    report_file = report_path or (
        runtime.storage_dir / "observability/editorial_ai_latest.json"
    )
    if not report_file.is_absolute():
        report_file = root / report_file
    report_file = report_file.resolve()
    report = read_json(report_file)

    if report.get("schema_name") != "outlet_editorial_ai.v1":
        raise ValueError(f"{report_file}: expected outlet_editorial_ai.v1")
    if report.get("site_id") != site_id:
        raise ValueError(f"{report_file}: site_id does not match {site_id}")
    draft_paths = report.get("draft_paths")
    if not isinstance(draft_paths, list) or not draft_paths:
        raise ValueError(f"{report_file}: no accepted draft_paths to preview")
    if int(report.get("accepted_count") or 0) != len(draft_paths):
        raise ValueError(f"{report_file}: accepted_count does not match draft_paths")

    digest_at = str(report.get("digest_at") or "").strip()
    if not digest_at:
        raise ValueError(f"{report_file}: missing digest_at")

    # Recompile the source snapshot from the same downloaded prepared runtime.
    # This prevents an AI cohort from being previewed on top of stale monitored
    # signals from an older local digest. It only mutates derived runtime indexes
    # and the runtime public snapshot; it never writes the published article bus.
    compile_result = compile_outlet(
        repo_root=root,
        site_id=site_id,
        digest_at=digest_at,
    )

    if not runtime.snapshot_path.is_file():
        raise ValueError("matching source snapshot was not produced")
    base_snapshot = read_json(runtime.snapshot_path)
    if base_snapshot.get("digest_at") != digest_at:
        raise ValueError(
            f"compiled snapshot digest {base_snapshot.get('digest_at')!r} "
            f"does not match prepared AI digest {digest_at!r}"
        )

    # Materialize canonical identity/presentation and that same-digest source
    # snapshot first. The preview overlay happens only inside apps/news_site.
    materialize(repo_root=root, site_id=site_id)

    app = root / "apps/news_site"
    snapshot_path = app / "public/data/site_snapshot.json"
    presentation_path = app / "config/site_presentation.json"
    snapshot = read_json(snapshot_path)
    presentation = read_json(presentation_path)

    previews: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    for ordinal, path_value in enumerate(draft_paths, start=1):
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError(f"{report_file}: draft_paths contains an invalid value")
        draft_path = resolve_draft_path(root, runtime.storage_dir, path_value)
        article = preview_article(read_one_jsonl(draft_path), ordinal=ordinal)
        if article["slug"] in seen_slugs:
            raise ValueError(f"duplicate prepared preview slug: {article['slug']}")
        seen_slugs.add(article["slug"])
        previews.append(article)

    previews.sort(
        key=lambda row: (str(row["published_at"]), str(row["article_id"])),
        reverse=True,
    )

    preview_articles = {
        str(article["slug"]): article
        for article in sorted(previews, key=lambda row: str(row["slug"]))
    }
    snapshot["articles"] = preview_articles
    snapshot["publication"] = {
        "featured": publication_ref(previews[0]),
        "latest": [publication_ref(article) for article in previews],
    }
    snapshot["metrics"]["published_article_count"] = len(previews)
    snapshot["snapshot_id"] = canonical_id(snapshot)
    validate_schema(snapshot)

    presentation.update(
        {
            "preview_mode": "prepared_issue",
            "preview_label": "BORRADORES IA · NO PUBLICADO",
            "preview_digest_at": report["digest_at"],
            "preview_draft_count": len(previews),
        }
    )

    atomic_json(snapshot_path, snapshot)
    atomic_json(presentation_path, presentation)

    return {
        "schema_name": "southland_prepared_issue_preview.v1",
        "status": "ok",
        "site_id": site_id,
        "digest_at": digest_at,
        "base_snapshot_id": compile_result["snapshot_id"],
        "workflow_id": report.get("workflow_id"),
        "model": report.get("model"),
        "accepted_count": len(previews),
        "draft_ids": [row["draft_id"] for row in previews],
        "titles": [row["title"] for row in previews],
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_path": str(snapshot_path),
        "presentation_path": str(presentation_path),
        "published_bus_mutated": False,
        "warning": "LOCAL PREVIEW ONLY — AI DRAFTS HAVE NOT BEEN HUMAN-APPROVED OR PUBLISHED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--site-id", default="southland")
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if args.confirm != CONFIRM:
        raise SystemExit(f"refusing preview without --confirm {CONFIRM}")
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        raise SystemExit("refusing to materialize unpublished AI drafts inside Vercel")

    try:
        result = materialize_preview(
            repo_root=args.repo_root,
            site_id=args.site_id,
            report_path=args.report,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema_name": "southland_prepared_issue_preview.v1",
                    "status": "failed",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
