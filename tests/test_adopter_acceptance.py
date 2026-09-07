from pathlib import Path

import pytest
import yaml

from scripts.adopter_intake import load_intake
from scripts.evaluate_adopter_acceptance import canonical_sha256, evaluate


REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "docs" / "adoption" / "adopter_acceptance.template.yaml"
INTAKE = REPO / "docs" / "adoption" / "adopter_intake.example.yaml"


def _load_template() -> dict:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _real_external_record(tmp_path: Path) -> tuple[Path, dict]:
    intake_payload = load_intake(INTAKE)
    intake_path = tmp_path / "real_adopter_intake.yaml"
    intake_path.write_text(yaml.safe_dump(intake_payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

    record = _load_template()
    record["status"] = "accepted"
    record["evidence_class"] = "real_external"
    record["adopter"] = {
        "organization": "Unit Test External Adopter",
        "adopter_ref": "external-adopter-ref-001",
    }
    record["intake"] = {
        "path": str(intake_path),
        "sha256": canonical_sha256(intake_payload),
        "completed": True,
    }
    record["preview"] = {
        "url": "https://pilot.unit-test-adopter.co/",
        "status": "verified",
        "site_id": "unit-test-adopter",
        "commit_sha": "abcdef0123456789abcdef0123456789abcdef01",
        "identity_verified": True,
        "owner_identity_leakage_absent": True,
        "evidence_ref": "preview-verification-record-001",
    }
    record["source"] = {
        "mode": "adopter_provided_feed",
        "evidence_ref": "provider-import-run-set-001",
        "repeated_successful_cycles": 5,
        "provider_rights_confirmed_by_human": True,
    }
    record["operator"] = {
        "non_developer_operator": True,
        "review_cycle_exercised": True,
        "no_storage_database_surgery": True,
        "evidence_ref": "operator-exercise-record-001",
    }
    record["delivery"] = {
        "deliverable_type": "html_email_brief",
        "artifact_sha256": "a" * 64,
        "status": "delivered",
        "provider_message_ref": "provider-message-001",
        "recipient_confirmed_useful": True,
        "evidence_ref": "delivery-receipt-record-001",
    }
    record["procurement"] = {
        "packet_reviewed_by_external_evaluator": True,
        "unresolved_blockers": [],
        "evidence_ref": "external-diligence-review-001",
    }
    record["transaction"] = {
        "commercial_path": "bounded_paid_pilot",
        "accepted_scope_or_contract": True,
        "external_document_ref": "external-scope-document-001",
        "owner_acceptance_ref": "owner-acceptance-001",
        "counterparty_acceptance_ref": "counterparty-acceptance-001",
    }
    record["deviations"] = [
        {
            "summary": "Reusable test requirement",
            "classification": "reusable_core",
            "status": "documented",
            "evidence_ref": "deviation-001",
        },
        {
            "summary": "Adopter-specific presentation request",
            "classification": "adopter_specific",
            "status": "resolved",
            "evidence_ref": "deviation-002",
        },
    ]
    record["acceptance"] = {
        "human_acceptance_recorded": True,
        "accepted_by": "unit-test-human-acceptor",
        "accepted_at": "2026-09-07T06:00:00Z",
        "note": "Synthetic unit-test evidence only; not a committed adopter claim.",
    }
    record_path = _write(tmp_path / "acceptance.yaml", record)
    return record_path, record


def test_pending_template_evaluates_as_pending_with_missing_real_world_evidence(tmp_path: Path) -> None:
    result = evaluate(TEMPLATE, output_dir=tmp_path / "report")

    assert result["evaluation_status"] == "pending_real_adopter_evidence"
    assert result["accepted"] is False
    assert result["customer_or_adopter_claim_allowed"] is False
    assert result["program_completion_allowed"] is False
    assert result["missing_count"] > 10
    assert any("evidence_class must be real_external" in item for item in result["missing_for_acceptance"])
    report = (tmp_path / "report" / "acceptance_report.md").read_text(encoding="utf-8")
    assert "Accepted: **false**" in report
    assert "pending_real_adopter_evidence" in report


def test_representative_test_record_cannot_claim_accepted_status(tmp_path: Path) -> None:
    record_path, record = _real_external_record(tmp_path)
    record["evidence_class"] = "representative_test"
    _write(record_path, record)

    with pytest.raises(ValueError, match="evidence_class=real_external"):
        evaluate(record_path, confirm_real_external_evidence=True)


def test_real_external_accepted_record_requires_explicit_confirmation_flag(tmp_path: Path) -> None:
    record_path, _ = _real_external_record(tmp_path)

    with pytest.raises(ValueError, match="--confirm-real-external-evidence"):
        evaluate(record_path)

    result = evaluate(record_path, confirm_real_external_evidence=True)
    assert result["accepted"] is True
    assert result["evaluation_status"] == "accepted_real_external_evidence_confirmed"
    assert result["missing_count"] == 0
    assert result["real_external_confirmation_used"] is True
    assert result["customer_or_adopter_claim_allowed"] is True
    assert result["program_completion_allowed"] is True


def test_intake_sha_mismatch_blocks_accepted_status(tmp_path: Path) -> None:
    record_path, record = _real_external_record(tmp_path)
    record["intake"]["sha256"] = "0" * 64
    _write(record_path, record)

    with pytest.raises(ValueError, match="intake.sha256"):
        evaluate(record_path, confirm_real_external_evidence=True)


def test_unresolved_blocking_deviation_blocks_acceptance(tmp_path: Path) -> None:
    record_path, record = _real_external_record(tmp_path)
    record["deviations"][0]["status"] = "unresolved_blocking"
    _write(record_path, record)

    with pytest.raises(ValueError, match="unresolved_blocking"):
        evaluate(record_path, confirm_real_external_evidence=True)


def test_reserved_preview_url_blocks_acceptance(tmp_path: Path) -> None:
    record_path, record = _real_external_record(tmp_path)
    record["preview"]["url"] = "https://example.com/fake-pilot"
    _write(record_path, record)

    with pytest.raises(ValueError, match="preview.url"):
        evaluate(record_path, confirm_real_external_evidence=True)


def test_pending_report_splits_reusable_and_adopter_specific_deviations(tmp_path: Path) -> None:
    record = _load_template()
    record["deviations"] = [
        {
            "summary": "Generic connector validation improvement",
            "classification": "reusable_core",
            "status": "documented",
            "evidence_ref": "human_evidence_required_reusable",
        },
        {
            "summary": "One-off brand typography request",
            "classification": "adopter_specific",
            "status": "documented",
            "evidence_ref": "human_evidence_required_specific",
        },
    ]
    record_path = _write(tmp_path / "pending.yaml", record)
    out = tmp_path / "evaluation"

    result = evaluate(record_path, output_dir=out)
    assert result["accepted"] is False

    reusable = yaml.safe_load((out / "reusable_backlog.yaml").read_text(encoding="utf-8"))
    specific = yaml.safe_load((out / "adopter_specific_followups.yaml").read_text(encoding="utf-8"))
    assert len(reusable["items"]) == 1
    assert reusable["items"][0]["classification"] == "reusable_core"
    assert len(specific["items"]) == 1
    assert specific["items"][0]["classification"] == "adopter_specific"
