from pathlib import Path

import pytest
import yaml

from scripts.build_transaction_packet import build_packet, validate_packet


REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / "docs" / "adoption" / "adopter_intake.example.yaml"


def test_paid_pilot_intake_compiles_to_executable_no_contract_scope_packet(tmp_path: Path) -> None:
    out = tmp_path / "transaction"
    manifest = build_packet(INTAKE, out)

    assert manifest["status"] == "ready_for_human_terms_and_counterparty_scoping"
    assert manifest["transaction_mode"] == "bounded_paid_pilot"
    assert manifest["contract_formed"] is False
    assert manifest["software_rights_granted"] is False
    assert manifest["payment_obligation_created"] is False
    assert manifest["signatures_present"] is False
    assert manifest["human_terms_required"] is True

    scope = (out / "scope_and_acceptance.md").read_text(encoding="utf-8")
    assert "14 days" in scope
    assert "90 minutes" in scope
    assert "minimum successful scheduled cycles: **5**" in scope
    assert "html_email_brief" in scope
    assert "no contract formed" in scope.lower()

    result = validate_packet(out)
    assert result["status"] == "ok"
    assert result["transaction_mode"] == "bounded_paid_pilot"
    assert result["human_term_count"] >= 15
    assert result["contract_formed"] is False


def test_transaction_packet_keeps_price_license_support_and_signatures_human(tmp_path: Path) -> None:
    out = tmp_path / "transaction"
    build_packet(INTAKE, out)
    terms = yaml.safe_load((out / "human_terms.yaml").read_text(encoding="utf-8"))

    for field in (
        "price",
        "currency",
        "invoice_schedule",
        "payment_terms",
        "repository_or_software_license",
        "commercial_license_grant",
        "source_code_rights",
        "support_scope",
        "uptime_or_freshness_sla",
        "privacy_and_data_processing_terms",
        "warranty",
        "indemnity_and_liability",
        "owner_acceptance",
        "counterparty_acceptance",
    ):
        assert terms[field] == "human_decision_required"

    assert terms["agent_may_fill_these_terms"] is False
    assert terms["contract_formed"] is False
    assert terms["software_rights_granted"] is False
    assert terms["payment_obligation_created"] is False


def test_responsibility_matrix_carries_intake_owners_without_contractualizing_them(tmp_path: Path) -> None:
    out = tmp_path / "transaction"
    build_packet(INTAKE, out)
    matrix = yaml.safe_load((out / "responsibility_matrix.yaml").read_text(encoding="utf-8"))
    rows = {row["area"]: row for row in matrix["rows"]}

    assert rows["source_input_or_provider_export"]["provisional_owner"] == "adopter"
    assert rows["recipient_send_or_provider_operation"]["provisional_owner"] == "media_monitor_pilot"
    assert rows["operator_review"]["provisional_owner"] == "analyst"
    assert all(row["contractual_allocation"] == "human_decision_required" for row in matrix["rows"])


def test_asset_inventory_grants_no_rights_or_secrets(tmp_path: Path) -> None:
    out = tmp_path / "transaction"
    build_packet(INTAKE, out)
    assets = yaml.safe_load((out / "asset_inventory.yaml").read_text(encoding="utf-8"))

    assert assets["rights_granted_by_this_inventory"] is False
    assert assets["secrets_included_in_transfer_packet"] is False
    assert assets["provider_credentials_included_in_transfer_packet"] is False
    assert assets["software_or_source_code_grant"] == "human_decision_required"
    assert assets["historical_corpus_inclusion"] == "human_decision_required"


def test_validator_refuses_agent_filled_price_even_if_packet_was_otherwise_valid(tmp_path: Path) -> None:
    out = tmp_path / "transaction"
    build_packet(INTAKE, out)
    terms_path = out / "human_terms.yaml"
    terms = yaml.safe_load(terms_path.read_text(encoding="utf-8"))
    terms["price"] = "USD 1000"
    terms_path.write_text(yaml.safe_dump(terms, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="human_terms.price"):
        validate_packet(out)


def test_exploratory_undecided_intake_cannot_masquerade_as_transaction_ready(tmp_path: Path) -> None:
    intake = yaml.safe_load(INTAKE.read_text(encoding="utf-8"))
    intake["commercial_path"]["evaluating"] = "exploratory_undecided"
    intake_path = tmp_path / "undecided.yaml"
    intake_path.write_text(yaml.safe_dump(intake, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match="selected commercial path"):
        build_packet(intake_path, tmp_path / "transaction")
