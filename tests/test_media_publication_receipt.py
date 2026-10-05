from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from emit_media_publication_receipt import build_receipt, validate_receipt


START = "2026-10-04T22:00:00Z"
FINISH = "2026-10-04T22:10:00Z"
DIGEST = "20261004T22"
SITE = "argentina-general"


def guard(status: str = "ok") -> dict:
    return {
        "schema_name": "publication_cycle_guard.v1",
        "status": status,
        "site_id": SITE,
        "digest_at": DIGEST,
        "error": "PRIVATE SOURCE ERROR" if status != "ok" else None,
    }


def roll(status: str = "ok") -> dict:
    return {
        "schema_name": "site_roll.v1",
        "status": status,
        "site_id": SITE,
        "target": "production",
        "digest_at": DIGEST,
        "snapshot_id": "a" * 64,
        "deployment_host": "private-host.example",
        "error": "VERCEL_TOKEN=do-not-copy" if status != "ok" else None,
    }


def public_check(status: str = "ok") -> dict:
    return {
        "schema_name": "public_deployment_check.v1",
        "status": status,
        "site_id": SITE,
        "digest_at": DIGEST,
        "freshness_status": "FRESH" if status == "ok" else "STALE",
        "within_target": status == "ok",
        "public_url": "https://private-ish.example",
        "error": "secret deployment detail" if status != "ok" else None,
    }


def crawler(status: str = "ok") -> dict:
    return {
        "schema_name": "crawler_surface_check.v1",
        "status": status,
        "base_url": "https://example.invalid",
        "article_status": "verified",
        "story_status": "verified",
        "article_text": "PRIVATE ARTICLE BODY",
        "error": "private crawler error" if status != "ok" else None,
    }


def receipt(**overrides):
    args = {
        "scheduler_run_id": "123456789",
        "run_attempt": "2",
        "event_name": "schedule",
        "job_status": "success",
        "started_at": START,
        "finished_at": FINISH,
        "site_id": SITE,
        "digest_at": DIGEST,
        "guard": guard(),
        "roll": roll(),
        "public_check": public_check(),
        "crawler": crawler(),
    }
    args.update(overrides)
    return build_receipt(**args)


def test_full_success_requires_all_semantic_evidence():
    value = receipt()
    assert value["result"] == {
        "scheduler_state": "healthy",
        "execution_state": "healthy",
        "artifact_state": "healthy",
        "terminal_state": "healthy",
        "authority_state": "canonical",
    }
    assert all(
        value["stages"][name] == "success"
        for name in ("predeploy_guard", "site_roll", "public_check", "crawler_surface")
    )
    states = {row["type"]: row["state"] for row in value["outputs"]}
    assert states["product.media-monitor-public-snapshot@1"] == "valid"
    assert states["evidence.media-monitor-cycle@1"] == "valid"
    validate_receipt(value)


def test_predeploy_guard_failure_blocks_artifact_health():
    value = receipt(guard=guard("failed"), job_status="failure")
    assert value["stages"]["predeploy_guard"] == "failed"
    assert value["result"]["execution_state"] == "failed"
    assert value["result"]["artifact_state"] == "failed"
    assert value["result"]["terminal_state"] == "failed"
    assert value["outputs"][0]["state"] == "invalid"


def test_public_deployment_failure_blocks_artifact_health():
    value = receipt(public_check=public_check("failed"), job_status="failure")
    assert value["stages"]["public_check"] == "failed"
    assert value["result"]["artifact_state"] == "failed"
    assert value["result"]["terminal_state"] == "failed"


def test_missing_evidence_never_promotes_artifact():
    value = receipt(public_check=None, crawler=None, job_status="failure")
    assert value["stages"]["public_check"] == "unknown"
    assert value["stages"]["crawler_surface"] == "unknown"
    assert value["result"]["artifact_state"] == "unknown"
    assert value["outputs"][0]["state"] == "unknown"
    assert value["result"]["terminal_state"] == "failed"


def test_identity_mismatch_is_failed_semantic_evidence():
    bad_roll = roll()
    bad_roll["digest_at"] = "20261004T21"
    value = receipt(roll=bad_roll)
    assert value["stages"]["site_roll"] == "failed"
    assert value["result"]["artifact_state"] == "failed"


def test_authority_and_workflow_identity_are_fixed_and_bounded():
    value = receipt(event_name="workflow_dispatch")
    assert value["producer_id"] == "producer.github.media-publication"
    assert value["scheduler_run_id"] == "123456789"
    assert value["run_id"] == "github-actions:matuteiglesias/media_monitor:123456789:2"
    assert value["trigger"] == "manual"
    assert value["result"]["authority_state"] == "canonical"


def test_source_payload_and_operational_secrets_do_not_enter_receipt():
    bad_guard = guard()
    bad_guard["prompt"] = "PRIVATE PROMPT"
    bad_roll = roll()
    bad_roll["VERCEL_TOKEN"] = "SUPERSECRET"
    bad_public = public_check()
    bad_public["source_payload"] = {"dataset_rows": ["PRIVATE"]}
    value = receipt(guard=bad_guard, roll=bad_roll, public_check=bad_public)
    rendered = json.dumps(value, sort_keys=True)
    for forbidden in (
        "PRIVATE PROMPT",
        "SUPERSECRET",
        "dataset_rows",
        "PRIVATE ARTICLE BODY",
        "private-host.example",
        "private-ish.example",
    ):
        assert forbidden not in rendered


def test_cancelled_execution_is_degraded_but_semantic_artifact_can_remain_healthy():
    value = receipt(job_status="cancelled")
    assert value["result"]["execution_state"] == "degraded"
    assert value["result"]["artifact_state"] == "healthy"
    assert value["result"]["terminal_state"] == "degraded"


def test_workflow_emits_receipt_under_always_and_uploads_it():
    workflow = (ROOT / ".github/workflows/scheduled-publication.yml").read_text(encoding="utf-8")
    assert "Capture producer receipt start" in workflow
    assert "Reset mutable publication-cycle evidence" in workflow
    assert "Emit governed producer receipt" in workflow
    emitter_at = workflow.index("Emit governed producer receipt")
    upload_at = workflow.index("Upload publication-cycle evidence")
    assert emitter_at < upload_at
    assert "scripts/emit_media_publication_receipt.py" in workflow
    assert "if: always()" in workflow
    assert "producer_receipts" in workflow
