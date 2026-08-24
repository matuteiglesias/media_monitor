#!/usr/bin/env python3
"""Guard scheduled source-site publication before any deployment side effect."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIGEST_RE = re.compile(r"^\d{8}T\d{2}$")


def parse_time(value: Any, label: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid timestamp {value!r}") from exc


def parse_digest(value: str) -> datetime:
    if not DIGEST_RE.fullmatch(value):
        raise ValueError(f"invalid digest_at {value!r}; expected YYYYMMDDTHH")
    return datetime.strptime(value, "%Y%m%dT%H").replace(tzinfo=timezone.utc)


def resolve_production_digest(now: datetime, requested: str | None = None) -> str:
    current = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    current_text = current.strftime("%Y%m%dT%H")
    if not requested:
        return current_text
    requested_dt = parse_digest(requested)
    if requested_dt != current:
        raise ValueError(
            "production refreshes must use the current UTC hour; "
            f"requested={requested} current={current_text}"
        )
    return requested


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"missing required input: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: empty JSONL")
    return rows


def topic_selected(topic: str, configured_topics: list[str]) -> bool:
    return "All Topics" in configured_topics or topic in configured_topics


def validate_predeploy(
    *,
    site_id: str,
    digest_at: str,
    repo_root: Path,
    now: datetime,
    target_minutes: int,
    previous_digest_at: str | None = None,
) -> dict[str, Any]:
    if target_minutes <= 0:
        raise ValueError("target_minutes must be positive")
    digest_dt = parse_digest(digest_at)
    now = now.astimezone(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    if digest_dt != current_hour:
        raise ValueError(
            "production digest is not the current UTC hour: "
            f"digest={digest_at} current={current_hour.strftime('%Y%m%dT%H')}"
        )
    if previous_digest_at and parse_digest(previous_digest_at) > digest_dt:
        raise ValueError(
            f"digest regression: previous={previous_digest_at} current={digest_at}"
        )

    root = repo_root.resolve()
    config_path = root / "sites" / f"{site_id}.json"
    config = read_json(config_path)
    if config.get("site_id") != site_id:
        raise ValueError(f"{config_path}: site_id mismatch")
    selection = config.get("selection") or {}
    topics = selection.get("topics")
    minimum_items = selection.get("minimum_items")
    if not isinstance(topics, list) or not topics:
        raise ValueError(f"{config_path}: selection.topics must be non-empty")
    if not isinstance(minimum_items, int) or minimum_items <= 0:
        raise ValueError(f"{config_path}: selection.minimum_items must be positive")

    refs_path = root / "storage" / "indexes" / "news_recent_refs_latest.jsonl"
    groups_path = root / "storage" / "indexes" / "news_recent_groups_latest.jsonl"
    refs = read_jsonl(refs_path)
    groups = read_jsonl(groups_path)

    for label, rows in (("refs", refs), ("groups", groups)):
        digests = {str(row.get("digest_at") or "").strip() for row in rows}
        if digests != {digest_at}:
            raise ValueError(
                f"{label} digest mismatch: expected={digest_at} observed={sorted(digests)}"
            )

    eligible = [
        row
        for row in refs
        if topic_selected(str(row.get("topic") or "").strip(), topics)
    ]
    if len(eligible) < minimum_items:
        raise ValueError(
            f"eligible refs below minimum: count={len(eligible)} minimum={minimum_items}"
        )

    published = [parse_time(row.get("published_at"), "published_at") for row in eligible]
    newest = max(published)
    if newest > now.replace(microsecond=0):
        future_minutes = (newest - now).total_seconds() / 60
        if future_minutes > 15:
            raise ValueError(
                f"newest monitored item is unexpectedly in the future by {future_minutes:.1f}m"
            )
    age_minutes = max(0.0, (now - newest).total_seconds() / 60)
    if age_minutes > target_minutes:
        raise ValueError(
            f"publication target missed before deploy: age={age_minutes:.1f}m "
            f"target={target_minutes}m newest={newest.isoformat()}"
        )

    group_topics = {str(row.get("topic") or "").strip() for row in groups}
    if not any(topic_selected(topic, topics) for topic in group_topics):
        raise ValueError("no group section matches configured site topics")

    return {
        "schema_name": "publication_cycle_guard.v1",
        "status": "ok",
        "site_id": site_id,
        "digest_at": digest_at,
        "evaluated_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "target_minutes": target_minutes,
        "eligible_item_count": len(eligible),
        "group_count": len(groups),
        "newest_item_at": newest.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "newest_item_age_minutes": round(age_minutes, 2),
        "previous_digest_at": previous_digest_at,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def command_resolve(args: argparse.Namespace) -> int:
    now = parse_time(args.now, "--now") if args.now else datetime.now(timezone.utc)
    try:
        print(resolve_production_digest(now, args.requested or None))
    except Exception as exc:
        print(f"[publication-cycle-guard] ERROR: {exc}")
        return 1
    return 0


def command_validate(args: argparse.Namespace) -> int:
    now = parse_time(args.now, "--now") if args.now else datetime.now(timezone.utc)
    output = Path(args.output)
    try:
        report = validate_predeploy(
            site_id=args.site_id,
            digest_at=args.digest_at,
            repo_root=Path(args.repo_root),
            now=now,
            target_minutes=args.target_minutes,
            previous_digest_at=args.previous_digest_at,
        )
    except Exception as exc:
        report = {
            "schema_name": "publication_cycle_guard.v1",
            "status": "failed",
            "site_id": args.site_id,
            "digest_at": args.digest_at,
            "evaluated_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "target_minutes": args.target_minutes,
            "error": str(exc),
        }
        write_report(output, report)
        print(f"[publication-cycle-guard] ERROR: {exc}")
        return 1
    write_report(output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--requested", default="")
    resolve.add_argument("--now")
    resolve.set_defaults(func=command_resolve)

    validate = sub.add_parser("validate")
    validate.add_argument("--site-id", required=True)
    validate.add_argument("--digest-at", required=True)
    validate.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    validate.add_argument("--target-minutes", type=int, default=120)
    validate.add_argument("--previous-digest-at")
    validate.add_argument(
        "--output",
        default="storage/observability/publication_cycle_guard_latest.json",
    )
    validate.add_argument("--now")
    validate.set_defaults(func=command_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
