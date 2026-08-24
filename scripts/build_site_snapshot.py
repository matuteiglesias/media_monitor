#!/usr/bin/env python3
"""Compile one digest-scoped public deployment snapshot.

site_snapshot.v2 deliberately separates two public classes:
- publication: human-approved published_article.v1 records only
- signals: monitored external-source news

Runtime freshness remains request-time state and is therefore not frozen into this
immutable snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def rows(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"missing required index: {path}")
    try:
        result = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSONL: {exc}") from exc
    if not result and not allow_empty:
        raise ValueError(f"{path}: empty JSONL")
    if not all(isinstance(row, dict) for row in result):
        raise ValueError(f"{path}: JSONL rows must be objects")
    return result


def parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: missing timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError as exc:
        raise ValueError(f"{label}: invalid timestamp {value!r}") from exc


def digest_set(items: list[dict[str, Any]], path: Path) -> str:
    values = {str(item.get("digest_at") or "").strip() for item in items}
    if "" in values or len(values) != 1:
        raise ValueError(
            f"{path}: expected exactly one non-empty digest_at, got {sorted(values)}"
        )
    return values.pop()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def validate_config(config: dict[str, Any]) -> None:
    for key in ("site_id", "name", "tagline", "locale", "selection", "presentation"):
        if key not in config:
            raise ValueError(f"site config missing {key}")
    selection = config["selection"]
    presentation = config["presentation"]
    if not isinstance(selection.get("topics"), list) or not selection["topics"]:
        raise ValueError("site config selection.topics must be non-empty")
    for key in ("max_age_hours", "minimum_items", "max_items"):
        if not isinstance(selection.get(key), int) or selection[key] < 0:
            raise ValueError(
                f"site config selection.{key} must be non-negative int"
            )
    if not 0 < selection["minimum_items"] <= selection["max_items"]:
        raise ValueError(
            "site config minimum_items must be positive and <= max_items"
        )
    if (
        not isinstance(presentation.get("latest_count"), int)
        or presentation["latest_count"] < 1
    ):
        raise ValueError("site config presentation.latest_count must be positive int")


def topic_selected(topic: str, configured: list[str]) -> bool:
    return "All Topics" in configured or topic in configured


def project_signal(row: dict[str, Any], label: str) -> dict[str, str]:
    required = ("index_id", "title", "topic", "published_at", "link")
    if any(not str(row.get(key) or "").strip() for key in required):
        raise ValueError(f"{label}: missing required signal field")
    parse_time(str(row["published_at"]), label)
    if urlparse(str(row["link"])).scheme not in {"http", "https"}:
        raise ValueError(f"{label}: invalid URL")
    return {
        key: str(row.get(key) or "").strip()
        for key in ("index_id", "title", "topic", "published_at", "link")
    } | {"source": str(row.get("source") or "").strip() or "unknown"}


def published_validator() -> Draft202012Validator:
    schema = read_json(ROOT / "contracts/schemas/published_article.v1.json")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_published_article(
    article: dict[str, Any], label: str, validator: Draft202012Validator
) -> None:
    errors = sorted(validator.iter_errors(article), key=lambda error: list(error.path))
    if errors:
        raise ValueError(
            f"{label}: not a valid published_article.v1: "
            + "; ".join(error.message for error in errors)
        )
    if article.get("schema_name") != "published_article.v1":
        raise ValueError(f"{label}: only published_article.v1 is eligible")
    if article.get("status") != "published":
        raise ValueError(f"{label}: article is not published")


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


def validate_schema(payload: dict[str, Any]) -> None:
    schema = read_json(ROOT / "contracts/schemas/site_snapshot.v2.json")
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            payload
        ),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError(
            "site snapshot schema validation failed: "
            + "; ".join(error.message for error in errors)
        )


def canonical_id(payload: dict[str, Any]) -> str:
    # generated_at is operational metadata; identical source inputs keep one stable ID.
    canonical = {
        key: value
        for key, value in payload.items()
        if key not in {"snapshot_id", "generated_at"}
    }
    return hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def build(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.sites_dir) / f"{args.site_id}.json"
    config = read_json(config_path)
    validate_config(config)
    if config["site_id"] != args.site_id:
        raise ValueError("site config site_id does not match --site-id")

    indexes_dir = Path(args.indexes_dir)
    refs_path = indexes_dir / "news_recent_refs_latest.jsonl"
    groups_path = indexes_dir / "news_recent_groups_latest.jsonl"
    published_path = indexes_dir / "published_articles_latest.jsonl"

    refs = rows(refs_path)
    groups = rows(groups_path)
    published_rows = rows(published_path, allow_empty=True)

    if (
        digest_set(refs, refs_path) != args.digest_at
        or digest_set(groups, groups_path) != args.digest_at
    ):
        raise ValueError("signal index digest_at does not match requested digest")

    now = parse_time(args.now, "--now") if args.now else datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=config["selection"]["max_age_hours"])
    configured_topics = config["selection"]["topics"]

    selected: list[dict[str, str]] = []
    seen_signals: set[str] = set()
    for index, row in enumerate(refs):
        item = project_signal(row, f"{refs_path}:{index + 1}")
        if not topic_selected(item["topic"], configured_topics):
            continue
        if parse_time(item["published_at"], item["index_id"]) < cutoff:
            continue
        if item["index_id"] in seen_signals:
            continue
        seen_signals.add(item["index_id"])
        selected.append(item)

    selected.sort(
        key=lambda item: (item["published_at"], item["index_id"]), reverse=True
    )
    selected = selected[: config["selection"]["max_items"]]
    if len(selected) < config["selection"]["minimum_items"]:
        raise ValueError(
            f"selected {len(selected)} signals; "
            f"minimum_items={config['selection']['minimum_items']}"
        )

    sections: list[dict[str, Any]] = []
    for row in groups:
        topic = str(row.get("topic") or "").strip()
        if not topic_selected(topic, configured_topics):
            continue
        sections.append(
            {
                "topic": topic,
                "article_count": int(row.get("article_count") or 0),
                "top_titles": [str(value) for value in (row.get("top_titles") or [])],
            }
        )
    sections.sort(key=lambda section: section["topic"])
    if not sections:
        raise ValueError("no selected signal sections")

    validator = published_validator()
    approved: list[dict[str, Any]] = []
    seen_article_ids: set[str] = set()
    seen_slugs: set[str] = set()
    for index, article in enumerate(published_rows):
        label = f"{published_path}:{index + 1}"
        # Fail closed if anything other than an approved public contract reaches this index.
        validate_published_article(article, label, validator)
        if not topic_selected(str(article["topic"]), configured_topics):
            continue
        article_id = str(article["article_id"])
        slug = str(article["slug"])
        if article_id in seen_article_ids:
            raise ValueError(f"{label}: duplicate article_id {article_id}")
        if slug in seen_slugs:
            raise ValueError(f"{label}: duplicate slug {slug}")
        seen_article_ids.add(article_id)
        seen_slugs.add(slug)
        approved.append(article)

    approved.sort(
        key=lambda article: (str(article["published_at"]), str(article["article_id"])),
        reverse=True,
    )
    publication_latest = [
        publication_ref(article)
        for article in approved[: config["presentation"]["latest_count"]]
    ]
    articles = {
        str(article["slug"]): article
        for article in sorted(approved, key=lambda article: str(article["slug"]))
    }

    payload: dict[str, Any] = {
        "schema_name": "site_snapshot.v2",
        "snapshot_id": "",
        "site": {
            key: config[key] for key in ("site_id", "name", "tagline", "locale")
        },
        "digest_at": args.digest_at,
        "generated_at": now.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "status": "ok",
        "metrics": {
            # item_count/section_count remain signal counts for P0-A/P0-B compatibility.
            "item_count": len(selected),
            "section_count": len(sections),
            "published_article_count": len(approved),
        },
        "publication": {
            "featured": publication_latest[0] if publication_latest else None,
            "latest": publication_latest,
        },
        "signals": {
            "hero": selected[0],
            "latest": selected[: config["presentation"]["latest_count"]],
            "sections": sections,
        },
        "articles": articles,
        "provenance": {
            "refs_path": str(refs_path),
            "refs_sha256": sha(refs_path),
            "groups_path": str(groups_path),
            "groups_sha256": sha(groups_path),
            "published_articles_path": str(published_path),
            "published_articles_sha256": sha(published_path),
            "git_sha": git_sha(),
        },
    }
    payload["snapshot_id"] = canonical_id(payload)
    validate_schema(payload)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--sites-dir", default="sites")
    parser.add_argument("--indexes-dir", default="storage/indexes")
    parser.add_argument(
        "--output", default="apps/news_site/public/data/site_snapshot.json"
    )
    parser.add_argument("--now")
    try:
        print(json.dumps(build(parser.parse_args()), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"[build-site-snapshot] ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
