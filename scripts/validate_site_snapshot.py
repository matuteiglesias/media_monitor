#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_site_snapshot import (
    canonical_id,
    parse_time,
    published_validator,
    read_json,
    rows,
    sha,
    story_context_validator,
    validate_config,
    validate_editorial_selection,
    validate_published_article,
    validate_schema,
    validate_story_context,
)


def validate_publication(snapshot: dict, latest_count: int) -> None:
    publication = snapshot["publication"]
    articles = snapshot["articles"]
    expected_count = snapshot["metrics"]["published_article_count"]
    if expected_count != len(articles):
        raise ValueError("published_article_count/articles mismatch")

    validator = published_validator()
    seen_ids: set[str] = set()
    for slug, article in articles.items():
        validate_published_article(article, f"articles.{slug}", validator)
        if article["slug"] != slug:
            raise ValueError(f"articles.{slug}: key does not match article slug")
        if article["article_id"] in seen_ids:
            raise ValueError(f"duplicate article_id {article['article_id']}")
        seen_ids.add(article["article_id"])

    latest = publication["latest"]
    if len(latest) != min(expected_count, latest_count):
        raise ValueError("publication.latest length mismatch")
    if expected_count == 0:
        if publication["featured"] is not None or latest:
            raise ValueError("empty publication must not expose featured/latest entries")
        return
    if not latest or publication["featured"] != latest[0]:
        raise ValueError("publication.featured must equal first publication.latest entry")

    previous_key: tuple[str, str] | None = None
    for ref in latest:
        slug = ref["slug"]
        article = articles.get(slug)
        if article is None:
            raise ValueError(f"publication.latest references missing article slug {slug}")
        expected = {
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
        if ref != expected:
            raise ValueError(f"publication ref does not match articles.{slug}")
        key = (ref["published_at"], ref["article_id"])
        if previous_key is not None and key > previous_key:
            raise ValueError("publication.latest is not deterministically newest-first")
        previous_key = key


def validate_curated(snapshot: dict, *, now: datetime, max_age_hours: int) -> dict[str, dict]:
    curated = snapshot["signals"]["curated"]
    expected_count = snapshot["metrics"]["curated_signal_count"]
    if len(curated) != expected_count:
        raise ValueError("curated_signal_count/signals.curated mismatch")
    if [item["rank"] for item in curated] != list(range(1, len(curated) + 1)):
        raise ValueError("signals.curated ranks must be contiguous and ordered")

    provenance = snapshot["provenance"]
    selection_path = Path(provenance["editorial_selection_path"])
    if not selection_path.exists():
        raise ValueError("editorial selection provenance path does not exist")
    if sha(selection_path) != provenance["editorial_selection_sha256"]:
        raise ValueError("editorial selection provenance hash mismatch")
    selection = read_json(selection_path)
    validate_editorial_selection(
        selection,
        path=selection_path,
        digest_at=snapshot["digest_at"],
        now=now,
        max_age_hours=max_age_hours,
    )
    if selection["selection_id"] != provenance["editorial_selection_id"]:
        raise ValueError("editorial selection id/provenance mismatch")
    if selection["policy"]["policy_sha256"] != provenance["editorial_selection_policy_sha256"]:
        raise ValueError("editorial selection policy hash/provenance mismatch")

    public_fields = ("rank", "index_id", "title", "topic", "published_at", "link", "source", "score", "score_components", "reason_codes")
    expected = [{key: item[key] for key in public_fields} for item in selection["selected"]]
    if curated != expected:
        raise ValueError("signals.curated does not match editorial_selection.v1 ordered projection")
    return {str(item["index_id"]): item for item in curated}


def validate_story_contexts(snapshot: dict, curated_by_id: dict[str, dict]) -> None:
    story_contexts = snapshot["story_contexts"]
    latest = snapshot["signals"]["latest"]
    expected_ids = [str(item["index_id"]) for item in latest]
    if snapshot["metrics"]["story_context_count"] != len(story_contexts):
        raise ValueError("story_context_count/story_contexts mismatch")
    if set(story_contexts) != set(expected_ids):
        raise ValueError("story_contexts keys must exactly match signals.latest index_ids")

    provenance = snapshot["provenance"]
    contexts_path = Path(provenance["story_contexts_path"])
    if not contexts_path.exists():
        raise ValueError("story contexts provenance path does not exist")
    if sha(contexts_path) != provenance["story_contexts_sha256"]:
        raise ValueError("story contexts provenance hash mismatch")
    source_rows = rows(contexts_path)
    source_by_id = {str(row.get("index_id") or ""): row for row in source_rows}

    validator = story_context_validator()
    for signal in latest:
        index_id = str(signal["index_id"])
        context = story_contexts[index_id]
        validate_story_context(
            context,
            label=f"story_contexts.{index_id}",
            digest_at=snapshot["digest_at"],
            validator=validator,
        )
        if context != source_by_id.get(index_id):
            raise ValueError(f"story_contexts.{index_id} does not match provenance artifact")
        if context["topic"] != signal["topic"]:
            raise ValueError(f"story_contexts.{index_id} topic does not match signal")
        curated = curated_by_id.get(index_id)
        expected_curation = {
            "selected": curated is not None,
            "rank": curated["rank"] if curated is not None else None,
            "score": curated["score"] if curated is not None else None,
            "reason_codes": curated["reason_codes"] if curated is not None else [],
        }
        if context["curation"] != expected_curation:
            raise ValueError(f"story_contexts.{index_id} curation mismatch")
        if context["provenance"]["editorial_selection_id"] != provenance["editorial_selection_id"]:
            raise ValueError(f"story_contexts.{index_id} selection provenance mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--sites-dir", default="sites")
    parser.add_argument("--input", default="apps/news_site/public/data/site_snapshot.json")
    parser.add_argument("--now")
    args = parser.parse_args()

    try:
        config = read_json(Path(args.sites_dir) / f"{args.site_id}.json")
        validate_config(config)
        snapshot = read_json(Path(args.input))
        validate_schema(snapshot)
        if snapshot["schema_name"] != "site_snapshot.v4":
            raise ValueError("expected site_snapshot.v4")
        if snapshot["site"]["site_id"] != args.site_id or snapshot["digest_at"] != args.digest_at:
            raise ValueError("snapshot site_id or digest_at does not match requested values")
        if snapshot["snapshot_id"] != canonical_id(snapshot):
            raise ValueError("snapshot_id is not deterministic canonical payload hash")

        signals = snapshot["signals"]
        signal_latest = signals["latest"]
        signal_sections = signals["sections"]
        item_count = snapshot["metrics"]["item_count"]
        section_count = snapshot["metrics"]["section_count"]
        if len(signal_latest) != min(item_count, config["presentation"]["latest_count"]):
            raise ValueError("item_count/signals.latest mismatch")
        if section_count != len(signal_sections):
            raise ValueError("section_count/signals.sections mismatch")
        if item_count < config["selection"]["minimum_items"]:
            raise ValueError("snapshot below configured minimum_items")
        if signals["hero"] != signal_latest[0]:
            raise ValueError("signals.hero must be first signals.latest item")

        now = parse_time(args.now, "--now") if args.now else datetime.now(timezone.utc)
        if now - parse_time(snapshot["generated_at"], "generated_at") > timedelta(hours=config["selection"]["max_age_hours"]):
            raise ValueError("snapshot age exceeds configured max_age_hours")
        for item in [signals["hero"], *signal_latest, *signals["curated"]]:
            if parse_time(item["published_at"], item["index_id"]) < now - timedelta(hours=config["selection"]["max_age_hours"]):
                raise ValueError("snapshot contains stale monitored signal")

        curated_by_id = validate_curated(
            snapshot,
            now=now,
            max_age_hours=config["selection"]["max_age_hours"],
        )
        validate_story_contexts(snapshot, curated_by_id)
        validate_publication(snapshot, config["presentation"]["latest_count"])

        print(json.dumps({
            "status": "ok",
            "snapshot_id": snapshot["snapshot_id"],
            "digest_at": snapshot["digest_at"],
            "item_count": item_count,
            "section_count": section_count,
            "published_article_count": snapshot["metrics"]["published_article_count"],
            "curated_signal_count": snapshot["metrics"]["curated_signal_count"],
            "story_context_count": snapshot["metrics"]["story_context_count"],
        }))
        return 0
    except Exception as exc:
        print(f"[validate-site-snapshot] ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
