#!/usr/bin/env python3
"""Verify the deployed public health endpoint without privileged Vercel access."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def validate_health(roll: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    if roll.get("status") != "ok":
        raise ValueError("roll record is not successful")
    host = str(roll.get("deployment_host") or "").strip()
    if not host:
        raise ValueError("roll record is missing deployment_host")

    roll_expected = roll.get("expected") or {}
    expected = {
        "status": "ok",
        "site_id": roll.get("site_id"),
        "digest_at": roll.get("digest_at"),
        "snapshot_id": roll.get("snapshot_id"),
        "item_count": roll_expected.get("item_count"),
        "section_count": roll_expected.get("section_count"),
        "published_article_count": roll_expected.get("published_article_count", 0),
    }
    mismatches = {
        key: {"expected": value, "observed": observed.get(key)}
        for key, value in expected.items()
        if observed.get(key) != value
    }
    if mismatches:
        raise ValueError(f"public health identity mismatch: {mismatches}")

    publication = observed.get("publication_health")
    if not isinstance(publication, dict):
        raise ValueError("public health is missing publication_health")
    if publication.get("schema_name") != "publication_health.v1":
        raise ValueError("unexpected publication health schema")
    if publication.get("freshness_status") != "FRESH":
        raise ValueError(
            f"deployed publication is not fresh: {publication.get('freshness_status')}"
        )
    if publication.get("is_current") is not True:
        raise ValueError("deployed publication does not claim current state")
    if publication.get("within_target") is not True:
        raise ValueError(
            f"deployed publication missed target: age_minutes={publication.get('age_minutes')}"
        )

    return {
        "schema_name": "public_deployment_check.v1",
        "status": "ok",
        "deployment_host": host,
        "site_id": expected["site_id"],
        "digest_at": expected["digest_at"],
        "snapshot_id": expected["snapshot_id"],
        "published_article_count": expected["published_article_count"],
        "freshness_status": publication.get("freshness_status"),
        "within_target": publication.get("within_target"),
        "age_minutes": publication.get("age_minutes"),
        "checked_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def fetch_health(host: str, timeout: float = 20.0) -> dict[str, Any]:
    request = Request(
        f"https://{host}/api/health",
        headers={"Accept": "application/json", "User-Agent": "media-monitor-public-check/1"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("public health response must be a JSON object")
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--roll-record",
        default="storage/observability/site_roll_latest_argentina-general.json",
    )
    parser.add_argument(
        "--output",
        default="storage/observability/public_deployment_check_latest.json",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    output = Path(args.output)
    try:
        roll = read_json(Path(args.roll_record))
        host = str(roll.get("deployment_host") or "").strip()
        if not host:
            raise ValueError("roll record is missing deployment_host")
        observed = fetch_health(host, args.timeout)
        report = validate_health(roll, observed)
    except Exception as exc:
        report = {
            "schema_name": "public_deployment_check.v1",
            "status": "failed",
            "checked_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "error": str(exc),
        }
        write_report(output, report)
        print(f"[public-deployment-check] ERROR: {exc}")
        return 1

    write_report(output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
