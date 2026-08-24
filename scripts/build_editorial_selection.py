#!/usr/bin/env python3
"""Build editorial_selection.v1 from monitored source-signal indexes.

This module is intentionally deterministic and non-LLM. Selection means only
"worth surfacing in the monitored frontier"; it never implies authorship,
editorial approval, or eligibility for published_article.v1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFS = Path("storage/indexes/news_recent_refs_latest.jsonl")
DEFAULT_POLICY = Path("config/editorial_selection.argentina.json")
DEFAULT_OUTPUT = Path("storage/indexes/editorial_selection_latest.json")
SCHEMA = ROOT / "contracts/schemas/editorial_selection.v1.json"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"missing signal index: {path}")
    result: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected object")
        result.append(value)
    return result


def parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: missing timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid timestamp {value!r}") from exc


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(payload: dict[str, Any]) -> str:
    canonical = {key: value for key, value in payload.items() if key != "selection_id"}
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_title(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).strip()


def validate_policy(policy: dict[str, Any]) -> None:
    required_ints = (
        "max_age_minutes",
        "future_tolerance_minutes",
        "minimum_items",
        "max_items",
        "high_priority_threshold",
        "default_topic_weight",
        "first_source_bonus",
        "first_topic_bonus",
        "repeat_source_penalty",
        "repeat_topic_penalty",
    )
    for key in ("policy_id", "policy_version"):
        if not isinstance(policy.get(key), str) or not policy[key].strip():
            raise ValueError(f"policy.{key} must be a non-empty string")
    for key in required_ints:
        if not isinstance(policy.get(key), int):
            raise ValueError(f"policy.{key} must be int")
    if policy["minimum_items"] < 1 or policy["minimum_items"] > policy["max_items"]:
        raise ValueError("policy minimum_items must be positive and <= max_items")
    if policy["max_age_minutes"] < 1 or policy["future_tolerance_minutes"] < 0:
        raise ValueError("policy age bounds are invalid")
    if policy["repeat_source_penalty"] < 0 or policy["repeat_topic_penalty"] < 0:
        raise ValueError("repeat penalties are configured as positive magnitudes")
    weights = policy.get("topic_weights")
    if not isinstance(weights, dict) or not all(
        isinstance(key, str) and isinstance(value, int) for key, value in weights.items()
    ):
        raise ValueError("policy.topic_weights must map strings to ints")
    buckets = policy.get("freshness_buckets")
    if not isinstance(buckets, list) or not buckets:
        raise ValueError("policy.freshness_buckets must be non-empty")
    previous = -1
    for bucket in buckets:
        if not isinstance(bucket, dict):
            raise ValueError("freshness bucket must be object")
        max_age = bucket.get("max_age_minutes")
        score = bucket.get("score")
        reason = bucket.get("reason_code")
        if not isinstance(max_age, int) or max_age <= previous:
            raise ValueError("freshness buckets must have ascending integer max_age_minutes")
        if not isinstance(score, int):
            raise ValueError("freshness bucket score must be int")
        if not isinstance(reason, str) or not re.fullmatch(r"[a-z0-9_]+", reason):
            raise ValueError("freshness reason_code must be snake_case")
        previous = max_age
    if buckets[-1]["max_age_minutes"] != policy["max_age_minutes"]:
        raise ValueError("last freshness bucket must end at policy.max_age_minutes")


def freshness_component(age_minutes: float, policy: dict[str, Any]) -> tuple[int, str]:
    for bucket in policy["freshness_buckets"]:
        if age_minutes <= bucket["max_age_minutes"]:
            return int(bucket["score"]), str(bucket["reason_code"])
    raise ValueError("eligible signal fell outside freshness buckets")


def project_candidate(row: dict[str, Any], *, as_of: datetime, policy: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    index_id = str(row.get("index_id") or "").strip()
    title = str(row.get("title") or "").strip()
    topic = str(row.get("topic") or "").strip()
    link = str(row.get("link") or "").strip()
    source = str(row.get("source") or "").strip() or "unknown"
    if not all((index_id, title, topic, link)):
        return None, "missing_identity"
    published_at = parse_time(row.get("published_at"), index_id)
    age_minutes = (as_of - published_at).total_seconds() / 60.0
    if age_minutes < -policy["future_tolerance_minutes"]:
        raise ValueError(f"{index_id}: published_at is unexpectedly in the future")
    if age_minutes > policy["max_age_minutes"]:
        return None, "stale"
    return {
        "index_id": index_id,
        "title": title,
        "topic": topic,
        "published_at": published_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "published_dt": published_at,
        "link": link,
        "source": source,
        "age_minutes": max(age_minutes, 0.0),
        "title_key": normalize_title(title),
    }, None


def deduplicate(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    by_title: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = candidate["title_key"] or candidate["index_id"]
        by_title.setdefault(key, []).append(candidate)
    kept: list[dict[str, Any]] = []
    removed = 0
    for values in by_title.values():
        values.sort(
            key=lambda item: (
                -item["published_dt"].timestamp(),
                item["source"].casefold(),
                item["index_id"],
                item["link"],
            )
        )
        kept.append(values[0])
        removed += len(values) - 1
    kept.sort(key=lambda item: (item["index_id"], item["link"]))
    return kept, removed


def score_candidate(
    candidate: dict[str, Any],
    *,
    policy: dict[str, Any],
    source_counts: Counter[str],
    topic_counts: Counter[str],
) -> tuple[int, dict[str, int], list[str]]:
    topic_priority = int(
        policy["topic_weights"].get(candidate["topic"], policy["default_topic_weight"])
    )
    freshness, freshness_reason = freshness_component(candidate["age_minutes"], policy)
    source_seen = source_counts[candidate["source"]]
    topic_seen = topic_counts[candidate["topic"]]
    first_source_bonus = int(policy["first_source_bonus"]) if source_seen == 0 else 0
    first_topic_bonus = int(policy["first_topic_bonus"]) if topic_seen == 0 else 0
    repeat_source_penalty = -int(policy["repeat_source_penalty"]) * source_seen
    repeat_topic_penalty = -int(policy["repeat_topic_penalty"]) * topic_seen
    components = {
        "topic_priority": topic_priority,
        "freshness": freshness,
        "first_source_bonus": first_source_bonus,
        "first_topic_bonus": first_topic_bonus,
        "repeat_source_penalty": repeat_source_penalty,
        "repeat_topic_penalty": repeat_topic_penalty,
    }
    score = sum(components.values())
    reasons = [freshness_reason]
    if topic_priority >= policy["high_priority_threshold"]:
        reasons.append("high_topic_priority")
    elif topic_priority > 0:
        reasons.append("standard_topic_priority")
    else:
        reasons.append("unweighted_topic")
    reasons.append("new_source_bonus" if source_seen == 0 else "repeat_source_penalty")
    reasons.append("new_topic_bonus" if topic_seen == 0 else "repeat_topic_penalty")
    return score, components, reasons


def select(candidates: list[dict[str, Any]], policy: dict[str, Any]) -> list[dict[str, Any]]:
    remaining = list(candidates)
    source_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < policy["max_items"]:
        evaluated: list[tuple[dict[str, Any], int, dict[str, int], list[str]]] = []
        for candidate in remaining:
            score, components, reasons = score_candidate(
                candidate,
                policy=policy,
                source_counts=source_counts,
                topic_counts=topic_counts,
            )
            evaluated.append((candidate, score, components, reasons))
        evaluated.sort(
            key=lambda value: (
                -value[1],
                -value[0]["published_dt"].timestamp(),
                value[0]["index_id"],
                value[0]["link"],
            )
        )
        candidate, score, components, reasons = evaluated[0]
        rank = len(selected) + 1
        selected.append(
            {
                "rank": rank,
                "index_id": candidate["index_id"],
                "title": candidate["title"],
                "topic": candidate["topic"],
                "published_at": candidate["published_at"],
                "link": candidate["link"],
                "source": candidate["source"],
                "score": score,
                "score_components": components,
                "reason_codes": reasons,
            }
        )
        source_counts[candidate["source"]] += 1
        topic_counts[candidate["topic"]] += 1
        remaining.remove(candidate)
    return selected


def validate_output(payload: dict[str, Any]) -> None:
    schema = read_json(SCHEMA)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError(
            "editorial selection schema validation failed: "
            + "; ".join(error.message for error in errors)
        )


def build(
    *,
    refs_path: Path,
    policy_path: Path,
    digest_at: str,
    as_of: str,
    output: Path,
) -> dict[str, Any]:
    rows = read_jsonl(refs_path)
    policy = read_json(policy_path)
    validate_policy(policy)
    as_of_dt = parse_time(as_of, "--as-of")
    digests = {str(row.get("digest_at") or "").strip() for row in rows}
    if rows and digests != {digest_at}:
        raise ValueError(f"{refs_path}: expected only digest_at={digest_at}, got {sorted(digests)}")

    projected: list[dict[str, Any]] = []
    stale_count = 0
    missing_identity_count = 0
    for row in rows:
        candidate, discard = project_candidate(row, as_of=as_of_dt, policy=policy)
        if discard == "stale":
            stale_count += 1
        elif discard == "missing_identity":
            missing_identity_count += 1
        elif candidate is not None:
            projected.append(candidate)

    eligible, deduplicated_count = deduplicate(projected)
    selected = select(eligible, policy)
    if len(selected) < policy["minimum_items"]:
        raise ValueError(
            f"selected {len(selected)} signals; minimum_items={policy['minimum_items']}"
        )

    policy_sha = sha256_file(policy_path)
    payload: dict[str, Any] = {
        "schema_name": "editorial_selection.v1",
        "selection_id": "",
        "digest_at": digest_at,
        "as_of": as_of_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_sha256": policy_sha,
        },
        "metrics": {
            "candidate_count": len(rows),
            "eligible_count": len(eligible),
            "deduplicated_count": deduplicated_count,
            "discarded_stale_count": stale_count,
            "discarded_missing_identity_count": missing_identity_count,
            "selected_count": len(selected),
        },
        "selected": selected,
        "provenance": {
            "refs_path": str(refs_path),
            "refs_sha256": sha256_file(refs_path),
            "policy_path": str(policy_path),
            "policy_sha256": policy_sha,
        },
    }
    payload["selection_id"] = canonical_hash(payload)
    validate_output(payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, output)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic monitored-signal editorial shortlist")
    parser.add_argument("--refs", default=str(DEFAULT_REFS))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--digest-at", required=True)
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        help="Evaluation instant. Pass explicitly for reproducible historical builds.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build(
            refs_path=Path(args.refs),
            policy_path=Path(args.policy),
            digest_at=args.digest_at,
            as_of=args.as_of,
            output=Path(args.output),
        )
    except Exception as exc:
        print(f"[editorial-selection] ERROR: {exc}")
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
