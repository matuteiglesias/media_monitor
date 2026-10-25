from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from emit_media_publication_receipt import build_receipt  # noqa: E402
from export_media_publication_gcp import (  # noqa: E402
    ExportError, PROJECT, build_entry, write_entry,
)

RUN = "123456789"
ATTEMPT = "2"
START = "2026-10-24T20:00:00Z"
FINISH = "2026-10-24T20:02:00Z"
DIGEST = "20261024T20"
SITE = "argentina-general"


def source(schema, **values):
    return {"schema_name": schema, "status": "ok", "site_id": SITE, "digest_at": DIGEST, **values}


def receipt(job_status="success", *, public_check=None):
    return build_receipt(
        scheduler_run_id=RUN, run_attempt=ATTEMPT,
        event_name="schedule", job_status=job_status,
        started_at=START, finished_at=FINISH,
        site_id=SITE, digest_at=DIGEST,
        guard=source("publication_cycle_guard.v1"),
        roll=source("site_roll.v1", target="production"),
        public_check=(source("public_deployment_check.v1", freshness_status="FRESH",
                             within_target=True) if public_check is None else public_check),
        crawler=source("crawler_surface_check.v1"),
    )


def test_contract_and_compatibility_projection_are_deterministic():
    a = build_entry(receipt(), run_id=RUN, attempt=ATTEMPT)
    b = build_entry(receipt(), run_id=RUN, attempt=ATTEMPT)
    assert a == b
    assert a["logName"] == f"projects/{PROJECT}/logs/estate-producer-run"
    assert len(a["insertId"]) == 64
    payload = a["jsonPayload"]
    assert payload["producer"] == {
        "producer_id": "producer.github.media-publication",
        "owner": "repo.media-monitor", "scheduler_kind": "github_actions",
        "observation_mode": "semantic_receipt", "authority_state": "canonical",
    }
    assert payload["receipt"] == receipt()
    assert a["severity"] == "INFO"


def test_failure_stays_failure_and_is_not_dropped():
    bad = source("public_deployment_check.v1", freshness_status="STALE", within_target=False)
    value = receipt("failure", public_check=bad)
    entry = build_entry(value, run_id=RUN, attempt=ATTEMPT)
    assert entry["severity"] == "ERROR"
    assert entry["jsonPayload"]["receipt"]["result"]["terminal_state"] == "failed"
    assert entry["jsonPayload"]["receipt"]["result"]["artifact_state"] == "failed"


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(producer_id="producer.other"),
    lambda x: x.update(run_id="github-actions:matuteiglesias/media_monitor:123:1"),
    lambda x: x["outputs"][0].update(content="PRIVATE BODY"),
    lambda x: x.update(raw_document="private"),
    lambda x: x["evidence_refs"].append("/home/person/file"),
    lambda x: x.update(warnings=["secret access_token: abc"]),
    lambda x: x["stages"].update(fake="success"),
])
def test_privacy_identity_and_unexpected_fields_fail_closed(mutation):
    value = receipt()
    mutation(value)
    with pytest.raises(ExportError):
        build_entry(value, run_id=RUN, attempt=ATTEMPT)


def test_http_transport_dry_run_write_and_failure():
    entry = build_entry(receipt(), run_id=RUN, attempt=ATTEMPT)
    session = Mock()
    session.post.return_value = Mock(ok=True, status_code=200)
    assert write_entry(session, entry, dry_run=True) == 200
    args, kwargs = session.post.call_args
    assert kwargs["params"] == {"dryRun": "true"}
    assert kwargs["json"]["entries"] == [entry]
    assert kwargs["json"]["partialSuccess"] is False
    assert write_entry(session, entry, dry_run=False) == 200
    assert session.post.call_args.kwargs["params"] is None
    session.post.return_value = Mock(ok=False, status_code=503)
    with pytest.raises(ExportError, match="503"):
        write_entry(session, entry, dry_run=False)


def test_matches_existing_central_exporter_insert_id(tmp_path):
    # Known identity from the bounded Oct 24 producer-owned receipt exported
    # by the central G2 transport. The receipt itself stays outside public git.
    candidate = Path("/tmp/obs-adoption-20261024/media/media-publication-40126992232-1.json")
    if not candidate.exists():
        pytest.skip("operator-only historic evidence file absent")
    value = json.loads(candidate.read_text())
    entry = build_entry(value, run_id="40126992232", attempt="1")
    assert entry["insertId"] == "827806b095c89333f8b7a53c7e716004994dc2983fb88fff06d666d892fd4860"


def test_workflow_is_bounded_and_nonblocking():
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/scheduled-publication.yml").read_text())
    steps = workflow["jobs"]["refresh-production"]["steps"]
    names = {s["name"]: s for s in steps if "name" in s}
    receipt_step = names["Emit governed producer receipt"]
    auth_step = names["Authenticate metadata receipt exporter (keyless)"]
    export_step = names["Export canonical publication receipt to GCP"]
    assert receipt_step["if"] == "always()"
    assert auth_step["continue-on-error"] is True
    assert export_step["continue-on-error"] is True
    assert "always()" in auth_step["if"] and "always()" in export_step["if"]
    assert steps.index(receipt_step) < steps.index(auth_step) < steps.index(export_step)
    assert steps.index(export_step) < steps.index(names["Upload publication-cycle evidence"])
    assert workflow["permissions"]["id-token"] == "write"
