import copy
import json
from pathlib import Path

import pytest
import yaml

from scripts.adopter_delivery import (
    AUTHORIZED_STATUS,
    PREPARED_STATUS,
    authorize_delivery,
    prepare_delivery,
    read_receipts,
    record_delivery,
)


REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / "docs" / "adoption" / "adopter_intake.example.yaml"
SNAPSHOT = REPO / "contracts" / "tests" / "fixtures" / "site_snapshot.v4.example.json"


def _intake(tmp_path: Path, *, target: str = "1-3") -> Path:
    payload = yaml.safe_load(INTAKE.read_text(encoding="utf-8"))
    payload["deliverables"][0]["target_item_count"] = target
    path = tmp_path / "intake.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _snapshot(tmp_path: Path, *, review_status: str = "human_approved") -> Path:
    payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    payload["articles"]["sample-article"]["review_status"] = review_status
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_prepare_recipient_brief_uses_only_human_approved_published_content(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"

    manifest = prepare_delivery(
        intake,
        snapshot,
        out,
        prepared_at="2026-01-15T12:50:00Z",
    )

    assert manifest["schema"] == "media_monitor_adopter_delivery.v1"
    assert manifest["status"] == PREPARED_STATUS
    assert manifest["send_eligible"] is False
    assert manifest["delivery_status"] == "not_sent"
    assert manifest["recipient_role"] == "executive_team"
    assert manifest["recipient_address"] is None
    assert manifest["content_authority"] == "published_article.v1_human_approved_only"
    assert manifest["item_count"] == 1
    assert manifest["article_ids"] == ["article-sample"]

    html = (out / "brief.html").read_text(encoding="utf-8")
    text = (out / "brief.txt").read_text(encoding="utf-8")
    assert "Example Intelligence Desk" in html
    assert "Sample article" in html
    assert "https://example.com/story" in html
    assert "Prepared artifact only" in html
    assert "Media Monitor" not in html
    assert "Sample article" in text
    assert not (out / "delivery_authorization.json").exists()
    assert not (out / "delivery_receipts.jsonl").exists()


def test_prepare_refuses_when_approved_content_does_not_meet_target_minimum(tmp_path: Path) -> None:
    intake = _intake(tmp_path, target="5-10")
    snapshot = _snapshot(tmp_path)

    with pytest.raises(ValueError, match="target requires at least 5"):
        prepare_delivery(intake, snapshot, tmp_path / "delivery")


def test_prepare_refuses_non_human_approved_publication_content(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path, review_status="pending")

    with pytest.raises(ValueError, match="not human-approved published content"):
        prepare_delivery(intake, snapshot, tmp_path / "delivery")


def test_delivery_authorization_requires_explicit_human_gate(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"
    prepare_delivery(intake, snapshot, out, prepared_at="2026-01-15T12:50:00Z")

    with pytest.raises(ValueError, match="--approve-delivery-human"):
        authorize_delivery(
            out / "delivery_manifest.json",
            out / "delivery_authorization.json",
            reviewer="pilot-editor",
            note="Reviewed recipient package.",
            approve_delivery_human=False,
        )


def test_authorization_binds_exact_manifest_and_does_not_claim_external_send(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"
    prepare_delivery(intake, snapshot, out, prepared_at="2026-01-15T12:50:00Z")

    authorization = authorize_delivery(
        out / "delivery_manifest.json",
        out / "delivery_authorization.json",
        reviewer="pilot-editor",
        note="Approved package for later external delivery.",
        approve_delivery_human=True,
        authorized_at="2026-01-15T12:55:00Z",
    )

    assert authorization["status"] == AUTHORIZED_STATUS
    assert authorization["authority"] == "explicit_human_delivery_authorization"
    assert authorization["external_send_performed"] is False
    assert len(authorization["manifest_sha256"]) == 64


def test_receipt_refuses_if_manifest_changed_after_authorization(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"
    prepare_delivery(intake, snapshot, out, prepared_at="2026-01-15T12:50:00Z")
    authorize_delivery(
        out / "delivery_manifest.json",
        out / "delivery_authorization.json",
        reviewer="pilot-editor",
        note="Approved exact prepared bytes.",
        approve_delivery_human=True,
        authorized_at="2026-01-15T12:55:00Z",
    )

    manifest = json.loads((out / "delivery_manifest.json").read_text(encoding="utf-8"))
    manifest["evidence_note"] = "tampered after authorization"
    (out / "delivery_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match current manifest bytes"):
        record_delivery(
            out / "delivery_manifest.json",
            out / "delivery_authorization.json",
            out / "delivery_receipts.jsonl",
            status="sent",
            actor="external-mail-operator",
            provider_message_ref="provider-msg-1",
            note="Provider accepted send.",
        )


def test_sent_receipt_requires_provider_reference(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"
    prepare_delivery(intake, snapshot, out, prepared_at="2026-01-15T12:50:00Z")
    authorize_delivery(
        out / "delivery_manifest.json",
        out / "delivery_authorization.json",
        reviewer="pilot-editor",
        note="Approved exact prepared bytes.",
        approve_delivery_human=True,
        authorized_at="2026-01-15T12:55:00Z",
    )

    with pytest.raises(ValueError, match="provider_message_ref"):
        record_delivery(
            out / "delivery_manifest.json",
            out / "delivery_authorization.json",
            out / "delivery_receipts.jsonl",
            status="sent",
            actor="external-mail-operator",
            provider_message_ref=None,
            note="Attempted send receipt without provider evidence.",
        )


def test_external_delivery_receipt_is_bound_to_authorized_artifact(tmp_path: Path) -> None:
    intake = _intake(tmp_path)
    snapshot = _snapshot(tmp_path)
    out = tmp_path / "delivery"
    prepare_delivery(intake, snapshot, out, prepared_at="2026-01-15T12:50:00Z")
    authorization = authorize_delivery(
        out / "delivery_manifest.json",
        out / "delivery_authorization.json",
        reviewer="pilot-editor",
        note="Approved exact prepared bytes.",
        approve_delivery_human=True,
        authorized_at="2026-01-15T12:55:00Z",
    )

    receipt = record_delivery(
        out / "delivery_manifest.json",
        out / "delivery_authorization.json",
        out / "delivery_receipts.jsonl",
        status="delivered",
        actor="external-mail-operator",
        provider_message_ref="provider-msg-42",
        note="Provider reports recipient delivery.",
        occurred_at="2026-01-15T13:00:00Z",
    )

    assert receipt["schema"] == "media_monitor_delivery_receipt.v1"
    assert receipt["status"] == "delivered"
    assert receipt["provider_message_ref"] == "provider-msg-42"
    assert receipt["source_snapshot_id"] == "a" * 64
    assert receipt["external_send_claim_source"] == "human_or_provider_supplied_evidence"
    assert receipt["authorization_sha256"]
    assert read_receipts(out / "delivery_receipts.jsonl") == [receipt]
