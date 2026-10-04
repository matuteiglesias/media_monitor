#!/usr/bin/env python3
"""Emit a metadata-only governed receipt for the scheduled publication producer.

The emitter translates producer-owned publication evidence into the estate
`evidence:producer-run-receipt@1` contract. It deliberately does not treat a
green GitHub Actions job as sufficient proof of artifact health.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT = "evidence:producer-run-receipt@1"
PRODUCER_ID = "producer.github.media-publication"
AUTHORITY_STATE = "canonical"
OUTPUTS = (
    ("product.media-monitor-public-snapshot@1", "served_current"),
    ("evidence.media-monitor-cycle@1", "run_evidence"),
)
STAGE_STATES = {"success", "failed", "skipped", "not_applicable", "unknown"}
OUTPUT_STATES = {"valid", "invalid", "partial", "missing", "unknown"}
RUN_STATES = {"healthy", "degraded", "failed", "unknown", "not_applicable"}
ARTIFACT_STATES = RUN_STATES | {"stale"}


class ReceiptError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptError(message)


def utciso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"unreadable evidence: {path.name}") from exc
    require(isinstance(value, dict), f"evidence must be a JSON object: {path.name}")
    return value


def stage_from_evidence(
    payload: dict[str, Any] | None,
    *,
    schema: str,
    expected_site: str | None = None,
    expected_digest: str | None = None,
    production_target: bool = False,
    public_freshness: bool = False,
) -> str:
    if payload is None:
        return "unknown"
    if payload.get("schema_name") != schema:
        return "failed"
    if expected_site and payload.get("site_id") != expected_site:
        return "failed"
    if expected_digest and payload.get("digest_at") != expected_digest:
        return "failed"
    if production_target and payload.get("target") != "production":
        return "failed"
    if payload.get("status") != "ok":
        return "failed"
    if public_freshness:
        if payload.get("freshness_status") != "FRESH":
            return "failed"
        if payload.get("within_target") is not True:
            return "failed"
    return "success"


def trigger_from_event(event_name: str) -> str:
    if event_name == "schedule":
        return "schedule"
    if event_name == "workflow_dispatch":
        return "manual"
    return "event"


def execution_from_job_status(job_status: str) -> tuple[str, str]:
    if job_status == "success":
        return "success", "healthy"
    if job_status == "failure":
        return "failed", "failed"
    if job_status == "cancelled":
        return "failed", "degraded"
    return "unknown", "unknown"


def evidence_ref(schema: str, digest_at: str | None, scheduler_run_id: str) -> str:
    identity = digest_at or f"github-run-{scheduler_run_id}"
    return f"media-monitor:{schema}:{identity}"


def validate_receipt(receipt: dict[str, Any]) -> None:
    required = {
        "contract", "run_id", "producer_id", "scheduler_run_id", "trigger",
        "started_at", "finished_at", "stages", "outputs", "result", "evidence_refs",
    }
    require(not (required - set(receipt)), "receipt is missing required fields")
    require(receipt["contract"] == CONTRACT, "unexpected receipt contract")
    require(receipt["producer_id"] == PRODUCER_ID, "unexpected producer id")
    require(isinstance(receipt["run_id"], str) and receipt["run_id"], "run_id is required")
    require(
        isinstance(receipt["scheduler_run_id"], str) and receipt["scheduler_run_id"],
        "scheduler_run_id is required",
    )
    require(receipt["trigger"] in {"schedule", "manual", "event"}, "invalid trigger")
    for field in ("started_at", "finished_at"):
        value = receipt[field]
        require(isinstance(value, str) and value, f"{field} is required")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, f"{field} must include timezone")
    require(
        all(value in STAGE_STATES for value in receipt["stages"].values()),
        "invalid stage state",
    )
    for output in receipt["outputs"]:
        require(output.get("state") in OUTPUT_STATES, "invalid output state")
    result = receipt["result"]
    require(result.get("scheduler_state") in RUN_STATES, "invalid scheduler state")
    require(result.get("execution_state") in RUN_STATES, "invalid execution state")
    require(result.get("artifact_state") in ARTIFACT_STATES, "invalid artifact state")
    require(result.get("terminal_state") in RUN_STATES, "invalid terminal state")
    require(result.get("authority_state") == AUTHORITY_STATE, "invalid authority state")
    rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in (
        "/home/", "\\users\\", "vercel_token", "api_key", "password",
        "secret", "transcript", "prompt", "article_text", "source_payload",
    ):
        require(forbidden not in rendered, f"receipt privacy violation: {forbidden}")


def build_receipt(
    *,
    scheduler_run_id: str,
    run_attempt: str,
    event_name: str,
    job_status: str,
    started_at: str,
    finished_at: str,
    site_id: str,
    digest_at: str | None,
    guard: dict[str, Any] | None,
    roll: dict[str, Any] | None,
    public_check: dict[str, Any] | None,
    crawler: dict[str, Any] | None,
) -> dict[str, Any]:
    workflow_stage, execution_state = execution_from_job_status(job_status)
    stages = {
        "workflow": workflow_stage,
        "predeploy_guard": stage_from_evidence(
            guard,
            schema="publication_cycle_guard.v1",
            expected_site=site_id,
            expected_digest=digest_at,
        ),
        "site_roll": stage_from_evidence(
            roll,
            schema="site_roll.v1",
            expected_site=site_id,
            expected_digest=digest_at,
            production_target=True,
        ),
        "public_check": stage_from_evidence(
            public_check,
            schema="public_deployment_check.v1",
            expected_site=site_id,
            expected_digest=digest_at,
            public_freshness=True,
        ),
        "crawler_surface": stage_from_evidence(
            crawler,
            schema="crawler_surface_check.v1",
        ),
    }

    semantic_states = [
        stages["predeploy_guard"],
        stages["site_roll"],
        stages["public_check"],
        stages["crawler_surface"],
    ]
    all_semantic_ok = all(state == "success" for state in semantic_states)
    any_semantic_failed = any(state == "failed" for state in semantic_states)
    any_semantic_unknown = any(state == "unknown" for state in semantic_states)

    if all_semantic_ok:
        artifact_state = "healthy"
        snapshot_state = "valid"
    elif any_semantic_failed:
        artifact_state = "failed"
        snapshot_state = "invalid"
    else:
        artifact_state = "unknown"
        snapshot_state = "unknown"

    if execution_state == "failed" or any_semantic_failed:
        terminal_state = "failed"
    elif execution_state == "healthy" and all_semantic_ok:
        terminal_state = "healthy"
    elif execution_state == "degraded" or any_semantic_unknown:
        terminal_state = "degraded"
    else:
        terminal_state = "unknown"

    warnings: list[str] = []
    for name in ("predeploy_guard", "site_roll", "public_check", "crawler_surface"):
        state = stages[name]
        if state != "success":
            warnings.append(f"{name} evidence is {state}.")
    if execution_state != "healthy":
        warnings.append(f"GitHub job execution state is {execution_state}.")

    refs = [f"github-actions:matuteiglesias/media_monitor:{scheduler_run_id}:attempt:{run_attempt}"]
    for payload, schema in (
        (guard, "publication_cycle_guard.v1"),
        (roll, "site_roll.v1"),
        (public_check, "public_deployment_check.v1"),
        (crawler, "crawler_surface_check.v1"),
    ):
        if payload is not None:
            refs.append(evidence_ref(schema, digest_at, scheduler_run_id))

    receipt = {
        "contract": CONTRACT,
        "run_id": f"github-actions:matuteiglesias/media_monitor:{scheduler_run_id}:{run_attempt}",
        "producer_id": PRODUCER_ID,
        "scheduler_run_id": scheduler_run_id,
        "trigger": trigger_from_event(event_name),
        "started_at": started_at,
        "finished_at": finished_at,
        "stages": stages,
        "outputs": [
            {
                "type": OUTPUTS[0][0],
                "state": snapshot_state,
                "durability": OUTPUTS[0][1],
            },
            {
                "type": OUTPUTS[1][0],
                "state": "valid",
                "durability": OUTPUTS[1][1],
            },
        ],
        "result": {
            "scheduler_state": "healthy",
            "execution_state": execution_state,
            "artifact_state": artifact_state,
            "terminal_state": terminal_state,
            "authority_state": AUTHORITY_STATE,
        },
        "warnings": warnings,
        "evidence_refs": refs,
    }
    validate_receipt(receipt)
    return receipt


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduler-run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--job-status", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at")
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", default="")
    parser.add_argument("--guard", type=Path, default=Path("storage/observability/publication_cycle_guard_latest.json"))
    parser.add_argument("--roll", type=Path, default=Path("storage/observability/site_roll_latest_argentina-general.json"))
    parser.add_argument("--public-check", type=Path, default=Path("storage/observability/public_deployment_check_latest.json"))
    parser.add_argument("--crawler", type=Path, default=Path("storage/observability/crawler_surface_check_latest.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--latest", type=Path)
    args = parser.parse_args()

    receipt = build_receipt(
        scheduler_run_id=args.scheduler_run_id,
        run_attempt=args.run_attempt,
        event_name=args.event_name,
        job_status=args.job_status,
        started_at=args.started_at,
        finished_at=args.finished_at or utciso(),
        site_id=args.site_id,
        digest_at=args.digest_at or None,
        guard=read_json(args.guard),
        roll=read_json(args.roll),
        public_check=read_json(args.public_check),
        crawler=read_json(args.crawler),
    )
    atomic_json(args.output, receipt)
    if args.latest:
        atomic_json(args.latest, receipt)
    print(json.dumps({
        "producer_id": receipt["producer_id"],
        "run_id": receipt["run_id"],
        "execution_state": receipt["result"]["execution_state"],
        "artifact_state": receipt["result"]["artifact_state"],
        "terminal_state": receipt["result"]["terminal_state"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
