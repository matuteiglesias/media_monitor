#!/usr/bin/env python3
"""Build a deterministic adopter-branded representative Media Monitor preview.

The preview exercises the real generic selection/context/site-snapshot compilers
from a validated adopter intake. It deliberately uses synthetic signals and does
not deploy, contact external services, or claim a live adopter/customer.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from adopter_intake import compile_plan, load_intake, load_schema, require_valid  # noqa: E402
from build_editorial_selection import build as build_selection  # noqa: E402
from build_site_snapshot import build as build_snapshot  # noqa: E402
from build_story_contexts import build as build_contexts  # noqa: E402


PREVIEW_DIGEST = "20260115T12"
PREVIEW_AS_OF = "2026-01-15T12:45:00Z"
PREVIEW_STATUS = "REPRESENTATIVE_FIXTURE_NOT_LIVE_ADOPTER"


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value[:48] or "adopter"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def synthetic_signals(intake: dict[str, Any], digest: str = PREVIEW_DIGEST) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    topics = [str(topic) for topic in intake["watch_policy"]["topics"]]
    max_age_minutes = max(1, int(math.ceil(float(intake["watch_policy"]["freshness_hours"]) * 60)))
    as_of = datetime.fromisoformat(PREVIEW_AS_OF.replace("Z", "+00:00")).astimezone(timezone.utc)

    signals: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for topic_index, topic in enumerate(topics):
        topic_titles: list[str] = []
        for variant in range(2):
            ordinal = topic_index * 2 + variant
            age_minutes = min(max_age_minutes - 1 if max_age_minutes > 1 else 0, 5 + ordinal * 3)
            published = as_of - timedelta(minutes=age_minutes)
            index_id = f"preview-{topic_index + 1}-{variant + 1}"
            title = f"Representative {topic} signal {variant + 1}"
            topic_titles.append(title)
            signals.append(
                {
                    "index_id": index_id,
                    "digest_at": digest,
                    "title": title,
                    "topic": topic,
                    "published_at": published.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "link": f"https://example.invalid/media-monitor-preview/{index_id}",
                    "source": f"Representative Source {topic_index + 1}-{variant + 1}",
                }
            )
        groups.append(
            {
                "digest_at": digest,
                "topic": topic,
                "article_count": len(topic_titles),
                "top_titles": topic_titles,
            }
        )
    return signals, groups


def site_config(intake: dict[str, Any], site_id: str, signal_count: int) -> dict[str, Any]:
    freshness_hours = max(1, int(math.ceil(float(intake["watch_policy"]["freshness_hours"]))))
    return {
        "site_id": site_id,
        "name": intake["identity"]["name"],
        "tagline": "Representative Media Monitor adopter preview — synthetic evidence only, not live news.",
        "locale": intake["identity"]["locale"],
        "selection": {
            "topics": list(intake["watch_policy"]["topics"]),
            "max_age_hours": freshness_hours,
            "minimum_items": min(3, signal_count),
            "max_items": min(12, signal_count),
        },
        "presentation": {
            "latest_count": min(8, signal_count),
            "show_sources": True,
        },
    }


def selection_policy(intake: dict[str, Any], site_id: str, signal_count: int) -> dict[str, Any]:
    max_age_minutes = max(1, int(math.ceil(float(intake["watch_policy"]["freshness_hours"]) * 60)))
    topics = list(intake["watch_policy"]["topics"])
    weights = {str(topic): max(1, 12 - index * 2) for index, topic in enumerate(topics)}
    return {
        "policy_id": f"{site_id}-representative-v1",
        "policy_version": "1",
        "max_age_minutes": max_age_minutes,
        "future_tolerance_minutes": 5,
        "minimum_items": min(3, signal_count),
        "max_items": min(6, signal_count),
        "high_priority_threshold": 10,
        "default_topic_weight": 0,
        "topic_weights": weights,
        "freshness_buckets": [
            {
                "max_age_minutes": max_age_minutes,
                "score": 20,
                "reason_code": "within_adopter_freshness_horizon",
            }
        ],
        "first_source_bonus": 6,
        "first_topic_bonus": 4,
        "repeat_source_penalty": 5,
        "repeat_topic_penalty": 2,
    }


def assert_identity_isolated(snapshot: dict[str, Any], intake: dict[str, Any]) -> None:
    site = snapshot.get("site") or {}
    if site.get("name") != intake["identity"]["name"]:
        raise ValueError("preview snapshot did not preserve adopter identity")
    if site.get("locale") != intake["identity"]["locale"]:
        raise ValueError("preview snapshot did not preserve adopter locale")
    encoded = json.dumps(snapshot, ensure_ascii=False).casefold()
    forbidden = ("matías iglesias", "matias iglesias", "análisis económico de argentina")
    leaked = [value for value in forbidden if value in encoded]
    if leaked:
        raise ValueError(f"preview contains Media Monitor owner/editor identity leakage: {leaked}")


def build_preview(intake_path: Path, output_dir: Path, *, replace: bool = False) -> dict[str, Any]:
    intake = load_intake(intake_path)
    require_valid(intake, load_schema())
    plan = compile_plan(intake)

    if output_dir.exists():
        if not replace:
            raise ValueError(f"output already exists: {output_dir}; pass --replace to rebuild")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    site_id = f"{slugify(intake['identity']['name'])}-{plan['source_intake_sha256'][:8]}"
    signals, groups = synthetic_signals(intake)
    if not signals:
        raise ValueError("validated intake produced no representative signals")

    sites_dir = output_dir / "sites"
    config_dir = output_dir / "config"
    indexes = output_dir / "storage" / "indexes"
    sites_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    indexes.mkdir(parents=True)

    site_path = sites_dir / f"{site_id}.json"
    policy_path = config_dir / "editorial_selection.json"
    refs_path = indexes / "news_recent_refs_latest.jsonl"
    groups_path = indexes / "news_recent_groups_latest.jsonl"
    published_path = indexes / "published_articles_latest.jsonl"
    selection_path = indexes / "editorial_selection_latest.json"
    contexts_path = indexes / "story_contexts_latest.jsonl"
    snapshot_path = output_dir / "site_snapshot.json"

    write_json(site_path, site_config(intake, site_id, len(signals)))
    write_json(policy_path, selection_policy(intake, site_id, len(signals)))
    write_jsonl(refs_path, signals)
    write_jsonl(groups_path, groups)
    published_path.write_text("", encoding="utf-8")

    selection = build_selection(
        refs_path=refs_path,
        policy_path=policy_path,
        digest_at=PREVIEW_DIGEST,
        as_of=PREVIEW_AS_OF,
        output=selection_path,
    )
    contexts = build_contexts(output_dir / "storage", PREVIEW_DIGEST, contexts_path)
    snapshot = build_snapshot(
        SimpleNamespace(
            site_id=site_id,
            digest_at=PREVIEW_DIGEST,
            sites_dir=str(sites_dir),
            indexes_dir=str(indexes),
            editorial_selection=str(selection_path),
            story_contexts=str(contexts_path),
            output=str(snapshot_path),
            now=PREVIEW_AS_OF,
        )
    )
    assert_identity_isolated(snapshot, intake)

    intake_copy = output_dir / "adopter_intake.yaml"
    intake_copy.write_text(yaml.safe_dump(intake, sort_keys=False, allow_unicode=True), encoding="utf-8")
    write_json(output_dir / "implementation_plan.json", plan)

    manifest = {
        "schema": "media_monitor_adopter_preview.v1",
        "status": PREVIEW_STATUS,
        "site_id": site_id,
        "name": snapshot["site"]["name"],
        "locale": snapshot["site"]["locale"],
        "source_intake_sha256": plan["source_intake_sha256"],
        "source_mode_requested": intake["sources"]["mode"],
        "fixture_mode": "synthetic_from_intake_topics",
        "digest_at": PREVIEW_DIGEST,
        "as_of": PREVIEW_AS_OF,
        "snapshot_id": snapshot["snapshot_id"],
        "signal_count": snapshot["metrics"]["item_count"],
        "curated_signal_count": snapshot["metrics"]["curated_signal_count"],
        "story_context_count": snapshot["metrics"]["story_context_count"],
        "selection_policy_id": selection["policy"]["policy_id"],
        "generic_builders": [
            "scripts/build_editorial_selection.py",
            "scripts/build_story_contexts.py",
            "scripts/build_site_snapshot.py",
        ],
        "identity_isolation_check": "passed",
        "deployment_status": "not_attempted",
        "live_source_status": "not_attempted",
        "customer_claim_allowed": False,
        "next_steps": plan["suggested_packet_order"],
        "outputs": {
            "site_config": str(site_path.relative_to(output_dir)),
            "selection_policy": str(policy_path.relative_to(output_dir)),
            "site_snapshot": str(snapshot_path.relative_to(output_dir)),
            "implementation_plan": "implementation_plan.json",
        },
    }
    write_json(output_dir / "preview_manifest.json", manifest)
    (output_dir / "README.txt").write_text(
        "\n".join(
            [
                "Media Monitor representative adopter preview",
                "",
                f"Status: {PREVIEW_STATUS}",
                "This package uses synthetic signals derived from the validated intake topics.",
                "It proves configuration/bootstrap and generic compiler reuse only.",
                "It is not live news, not a deployed customer instance, and not evidence of source integration.",
                "",
                "Inspect preview_manifest.json, implementation_plan.json, sites/, config/, and site_snapshot.json.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build_preview(args.intake, args.output, replace=args.replace)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
