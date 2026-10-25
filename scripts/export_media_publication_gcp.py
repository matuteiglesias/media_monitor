#!/usr/bin/env python3
"""Publish one existing semantic publication receipt to Cloud Logging.

Only the preexisting producer-run-receipt@1 metadata crosses this boundary.
This producer-specific adapter keeps the digest, insertId and jsonPayload
compatible with the central projects/G2 exporter without accessing its
private source repository from a public GitHub Actions workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from emit_media_publication_receipt import (
    CONTRACT, OUTPUTS, PRODUCER_ID, ReceiptError, validate_receipt,
)

PROJECT = "estate-observability-510700"
LOG_ID = "estate-producer-run"
ENDPOINT = "https://logging.googleapis.com/v2/entries:write"
WRITE_SCOPE = "https://www.googleapis.com/auth/logging.write"
OWNER = "repo.media-monitor"
EXPECTED_STAGES = frozenset(("workflow", "predeploy_guard", "site_roll", "public_check", "crawler_surface"))
EXPECTED_RESULT = frozenset((
    "scheduler_state", "execution_state", "artifact_state", "terminal_state", "authority_state",
))
EXPECTED_RECEIPT_KEYS = frozenset((
    "contract", "producer_id", "run_id", "scheduler_run_id", "trigger",
    "started_at", "finished_at", "stages", "outputs", "result", "evidence_refs", "warnings",
))
WARNING_PATTERN = re.compile(
    r"^(?:(?:predeploy_guard|site_roll|public_check|crawler_surface) evidence is "
    r"(?:failed|unknown|skipped|not_applicable)\.|"
    r"GitHub job execution state is (?:failed|degraded|unknown)\.)$"
)


class ExportError(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExportError(reason)


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_for_export(receipt: dict[str, Any], *, run_id: str, attempt: str) -> None:
    try:
        validate_receipt(receipt)
    except (ReceiptError, KeyError, TypeError, ValueError) as exc:
        raise ExportError("invalid canonical publication receipt") from exc
    require(set(receipt) == EXPECTED_RECEIPT_KEYS, "unexpected receipt metadata keys")
    require(re.fullmatch(r"[0-9]+", run_id) is not None, "invalid scheduler run ID")
    require(re.fullmatch(r"[1-9][0-9]*", attempt) is not None, "invalid attempt")
    require(receipt["scheduler_run_id"] == run_id, "receipt scheduler identity mismatch")
    require(
        receipt["run_id"] == f"github-actions:matuteiglesias/media_monitor:{run_id}:{attempt}",
        "receipt run/attempt identity mismatch",
    )
    require(set(receipt["stages"]) == EXPECTED_STAGES, "unexpected stage metadata")
    require(set(receipt["result"]) == EXPECTED_RESULT, "unexpected result metadata")
    require(len(receipt["outputs"]) == len(OUTPUTS), "unexpected output count")
    for actual, (artifact_type, durability) in zip(receipt["outputs"], OUTPUTS):
        require(isinstance(actual, dict) and set(actual) == {"type", "state", "durability"},
                "unexpected output fields")
        require(actual["type"] == artifact_type and actual["durability"] == durability,
                "unexpected output identity or durability")
    require(
        isinstance(receipt["warnings"], list)
        and all(isinstance(w, str) and WARNING_PATTERN.fullmatch(w) for w in receipt["warnings"]),
        "unsafe warning data",
    )
    refs = receipt["evidence_refs"]
    require(
        len(refs) <= 5 and len(refs) >= 1
        and refs[0] == f"github-actions:matuteiglesias/media_monitor:{run_id}:attempt:{attempt}",
        "unexpected evidence reference",
    )
    for ref in refs[1:]:
        require(
            ref.startswith("media-monitor:") and len(ref) <= 160
            and not any(fragment in ref.lower() for fragment in ("/home/", "token", "secret", "password")),
            "unsafe evidence reference",
        )
    # Defense in depth on the entire payload, even though the emitter already
    # restricts source values. Never carry raw publishing content to GCP.
    raw = canonical_json(receipt).lower()
    for fragment in (
        "/home/", "/users/", "\\users\\", '"command"', '"cwd"', '"environment"',
        '"api_key"', '"access_token"', '"password"', '"secret"', '"token"',
        '"credential"', '"transcript"', '"email_body"', '"messages"',
        '"dataset_rows"', '"raw_document"',
    ):
        require(fragment not in raw, "private or local data in receipt")


def build_entry(receipt: dict[str, Any], *, run_id: str, attempt: str) -> dict[str, Any]:
    validate_for_export(receipt, run_id=run_id, attempt=attempt)
    digest = hashlib.sha256(canonical_json(receipt).encode("utf-8")).hexdigest()
    identity = {
        "producer_id": receipt["producer_id"],
        "run_id": receipt["run_id"],
        "receipt_sha256": digest,
    }
    insert_id = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()
    result = receipt["result"]
    states = {result["execution_state"], result["artifact_state"], result["terminal_state"]}
    severity = "ERROR" if "failed" in states else ("WARNING" if states & {"unknown", "degraded"} else "INFO")
    return {
        "logName": f"projects/{PROJECT}/logs/{LOG_ID}",
        "resource": {"type": "global", "labels": {"project_id": PROJECT}},
        "timestamp": receipt["finished_at"],
        "severity": severity,
        "insertId": insert_id,
        "labels": {
            "producer_id": receipt["producer_id"],
            "receipt_sha256": digest,
            "source_contract": receipt["contract"],
        },
        "jsonPayload": {
            "contract": CONTRACT,
            "receipt": receipt,
            "receipt_sha256": digest,
            "logical_receipt_id": f"{receipt['producer_id']}:{receipt['run_id']}",
            "producer": {
                "producer_id": PRODUCER_ID,
                "owner": OWNER,
                "scheduler_kind": "github_actions",
                "observation_mode": "semantic_receipt",
                "authority_state": result["authority_state"],
            },
        },
    }


def write_entry(session: Any, entry: dict[str, Any], *, dry_run: bool) -> int:
    body = {
        "logName": f"projects/{PROJECT}/logs/{LOG_ID}",
        "resource": {"type": "global", "labels": {"project_id": PROJECT}},
        "entries": [entry],
        "partialSuccess": False,
    }
    response = session.post(
        ENDPOINT,
        params={"dryRun": "true"} if dry_run else None,
        json=body,
        timeout=30,
    )
    if not response.ok:
        # Do not print response content; remote text could contain private context.
        raise ExportError(f"Cloud Logging entries.write HTTP {response.status_code}")
    return response.status_code


def authorized_session() -> Any:
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials, _ = google.auth.default(scopes=[WRITE_SCOPE])
        return AuthorizedSession(credentials)
    except Exception as exc:
        raise ExportError("GCP keyless application credentials unavailable") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--scheduler-run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        require(isinstance(receipt, dict), "receipt input is not an object")
        entry = build_entry(receipt, run_id=args.scheduler_run_id, attempt=args.run_attempt)
        if args.write:
            session = authorized_session()
            write_entry(session, entry, dry_run=True)
            write_entry(session, entry, dry_run=False)
        print(json.dumps({
            "producer_id": PRODUCER_ID,
            "scheduler_run_id": args.scheduler_run_id,
            "insert_id": entry["insertId"],
            "mode": "exported" if args.write else "validated",
        }, sort_keys=True))
        return 0
    except (ExportError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"media publication receipt export failed: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
