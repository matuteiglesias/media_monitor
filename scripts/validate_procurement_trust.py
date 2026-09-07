#!/usr/bin/env python3
"""Validate the AP6 procurement/trust packet against repository evidence.

This validator is intentionally conservative. It verifies factual repository
claims and requires unresolved legal/commercial fields to remain explicit human
choices. It does not decide licensing, privacy, SLA, warranty, or pricing.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "docs" / "adoption" / "procurement_trust_state.yaml"
LICENSE_CANDIDATES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
)

DECISION_PATHS = (
    "repository.repository_level_license.decision",
    "repository.commercial_licensing_model.decision",
    "secrets_and_accounts.adopter_deployment_account_ownership.decision",
    "secrets_and_accounts.private_authentication_posture.decision",
    "third_party_dependencies.dependency_license_acceptance.decision",
    "source_data_and_provenance.data_rights_retention_and_permitted_use.decision",
    "editorial_and_delivery_authority.real_editorial_approval.decision",
    "editorial_and_delivery_authority.real_recipient_delivery_authorization.decision",
    "storage_retention_and_recovery.durability_or_cold_archive_commitment.decision",
    "storage_retention_and_recovery.adopter_data_retention_terms.decision",
    "support_incident_and_service_terms.support_model.decision",
    "support_incident_and_service_terms.support_hours.decision",
    "support_incident_and_service_terms.incident_response_commitment.decision",
    "support_incident_and_service_terms.uptime_or_freshness_sla.decision",
    "support_incident_and_service_terms.warranty_indemnity_and_liability.decision",
    "export_termination_and_handoff.contractual_export_package.decision",
    "export_termination_and_handoff.termination_handoff_obligation.decision",
    "export_termination_and_handoff.source_code_or_deployment_asset_transfer_scope.decision",
    "commercial_decisions.pricing.decision",
    "commercial_decisions.invoicing_and_payment_terms.decision",
    "commercial_decisions.attribution_and_white_label_terms.decision",
    "commercial_decisions.pilot_or_service_acceptance_terms.decision",
)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected YAML object")
    return value


def nested(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"packet missing required path: {dotted}")
        current = current[part]
    return current


def exact_pins(requirements_path: Path) -> list[str]:
    lines = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    bad = [line for line in lines if "==" not in line]
    if bad:
        raise ValueError(f"requirements-sensing.txt contains non-exact direct pins: {bad}")
    return lines


def validate_packet(packet_path: Path = DEFAULT_PACKET) -> dict[str, Any]:
    packet = load_yaml(packet_path)
    if packet.get("schema") != "media_monitor_procurement_trust.v1":
        raise ValueError("unexpected procurement packet schema")
    if packet.get("status") != "internal_diligence_packet_not_legal_or_commercial_commitment":
        raise ValueError("procurement packet status must preserve non-contract boundary")

    for path in DECISION_PATHS:
        if nested(packet, path) != "human_decision_required":
            raise ValueError(f"{path} must remain human_decision_required until explicitly resolved")

    evidence_paths = packet.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        raise ValueError("procurement packet must list evidence_paths")
    missing_evidence = [path for path in evidence_paths if not (ROOT / str(path)).exists()]
    if missing_evidence:
        raise ValueError(f"procurement evidence paths missing: {missing_evidence}")

    present_licenses = [name for name in LICENSE_CANDIDATES if (ROOT / name).exists()]
    license_status = nested(packet, "repository.repository_level_license.status")
    if present_licenses:
        if license_status == "unresolved_no_repository_level_license_file":
            raise ValueError(
                "repository license file now exists; procurement packet must be updated before claiming unresolved absence"
            )
    elif license_status != "unresolved_no_repository_level_license_file":
        raise ValueError("packet must state unresolved license absence while no repository-level license file exists")

    workflow_path = ROOT / ".github" / "workflows" / "scheduled-publication.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    required_workflow_fragments = {
        'cron: "45 * * * *"': "schedule_expression",
        "group: scheduled-publication-production": "concurrency_group",
        "timeout-minutes: 25": "timeout_minutes",
        'python-version: "3.12"': "python_version",
        'node-version: "20"': "scheduled_node_version",
        'VERCEL_CLI_VERSION: "59.11.7"': "vercel_cli_version",
        'PUBLICATION_TARGET_MINUTES: "120"': "public_freshness_implementation_target_minutes",
        "retention-days: 14": "github_publication_evidence_retention_days",
        "scripts/verify_public_deployment.py": "anonymous_public_verification_in_workflow",
        "scripts/verify_crawler_surface.py": "crawler_social_verification_in_workflow",
    }
    missing_fragments = [fragment for fragment in required_workflow_fragments if fragment not in workflow]
    if missing_fragments:
        raise ValueError(f"scheduled workflow drifted from procurement packet evidence: {missing_fragments}")

    for secret_name in packet["secrets_and_accounts"]["scheduled_publication_secret_names"]:
        if f"secrets.{secret_name}" not in workflow:
            raise ValueError(f"scheduled workflow no longer references expected secret name {secret_name}")

    if "python -m pip install -r requirements-sensing.txt jsonschema" not in workflow:
        raise ValueError("scheduled workflow jsonschema installation changed; update procurement pin-status fact")
    if nested(packet, "third_party_dependencies.scheduled_extra_jsonschema_pin_status") != "unpinned":
        raise ValueError("packet must record scheduled extra jsonschema as unpinned")

    pinned_requirements = exact_pins(ROOT / "requirements-sensing.txt")
    if nested(packet, "third_party_dependencies.python_sensing_direct_dependencies_exactly_pinned") is not True:
        raise ValueError("packet must record exact direct Python sensing pins")

    package = json.loads((ROOT / "apps" / "news_site" / "package.json").read_text(encoding="utf-8"))
    engine = ((package.get("engines") or {}).get("node"))
    if engine != nested(packet, "runtime_and_deployment.news_site_declared_node_engine"):
        raise ValueError("news-site Node engine drifted from procurement packet")
    scheduled_node = str(nested(packet, "runtime_and_deployment.scheduled_node_version"))
    if scheduled_node == str(engine):
        raise ValueError("packet says runtime mismatch is open but scheduled/runtime values are now equal; update AP6 facts")
    if nested(packet, "runtime_and_deployment.node_runtime_contract_status") != "mismatch_open":
        raise ValueError("Node runtime mismatch must remain explicit until fixed elsewhere")

    if nested(packet, "security_and_trust.certifications.status") != "none_claimed":
        raise ValueError("AP6 may not claim certifications without external evidence")
    if nested(packet, "runtime_and_deployment.public_freshness_is_contractual_sla") is not False:
        raise ValueError("implementation freshness target may not be represented as contractual SLA")
    if nested(packet, "storage_retention_and_recovery.github_publication_evidence_retention_days") != 14:
        raise ValueError("publication artifact retention fact drifted")

    return {
        "schema": "media_monitor_procurement_trust_validation.v1",
        "status": "ok",
        "packet": str(packet_path),
        "evidence_path_count": len(evidence_paths),
        "human_decision_count": len(DECISION_PATHS),
        "repository_license_files": present_licenses,
        "python_direct_pin_count": len(pinned_requirements),
        "scheduled_node_version": scheduled_node,
        "news_site_node_engine": engine,
        "node_runtime_contract_status": "mismatch_open",
        "publication_evidence_retention_days": 14,
        "contractual_sla_claimed": False,
        "certifications_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args()
    try:
        result = validate_packet(args.packet)
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
