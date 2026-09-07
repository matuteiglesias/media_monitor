#!/usr/bin/env python3
"""Compile a validated adopter intake into a no-contract transaction packet.

The packet makes scoping/acceptance/responsibility/handoff mechanics concrete,
but it deliberately grants no rights, chooses no price, creates no invoice, and
forms no contract. Human/legal/commercial terms remain explicit placeholders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from scripts.adopter_intake import load_intake, load_schema, require_valid


ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = "media_monitor_transaction_packet.v1"
TERMS_SCHEMA = "media_monitor_human_terms.v1"
RESPONSIBILITY_SCHEMA = "media_monitor_responsibility_matrix.v1"
ASSET_SCHEMA = "media_monitor_transfer_asset_inventory.v1"
READY_STATUS = "ready_for_human_terms_and_counterparty_scoping"

MODE_MAP = {
    "paid_pilot": "bounded_paid_pilot",
    "managed_white_label": "managed_deployment_service",
    "technology_license_partnership": "technology_license_partnership",
    "strategic_transfer": "strategic_asset_transfer",
}

HUMAN_TERM_FIELDS = (
    "price",
    "currency",
    "invoice_schedule",
    "payment_terms",
    "repository_or_software_license",
    "commercial_license_grant",
    "source_code_rights",
    "deployment_asset_rights",
    "data_rights_and_retention_terms",
    "privacy_and_data_processing_terms",
    "support_scope",
    "support_hours",
    "incident_commitment",
    "uptime_or_freshness_sla",
    "warranty",
    "indemnity_and_liability",
    "attribution_and_white_label_terms",
    "termination_terms",
    "post_termination_retention_or_deletion",
    "governing_law_or_venue",
    "owner_acceptance",
    "counterparty_acceptance",
)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def write_yaml(path: Path, value: Any) -> None:
    atomic_write(path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode("utf-8"))


def human_decision() -> str:
    return "human_decision_required"


def transaction_mode(intake: dict[str, Any]) -> str:
    evaluating = str(intake["commercial_path"]["evaluating"])
    if evaluating == "exploratory_undecided":
        raise ValueError("AP7 requires a selected commercial path before transaction packet compilation")
    try:
        return MODE_MAP[evaluating]
    except KeyError as exc:
        raise ValueError(f"unsupported commercial path: {evaluating}") from exc


def responsibility_matrix(intake: dict[str, Any], mode: str) -> dict[str, Any]:
    deployment_owner = intake["privacy"].get("deployment_account_owner") or human_decision()
    if deployment_owner == "undecided":
        deployment_owner = human_decision()
    return {
        "schema": RESPONSIBILITY_SCHEMA,
        "status": "scoping_not_contractual_allocation",
        "transaction_mode": mode,
        "rows": [
            {
                "area": "source_input_or_provider_export",
                "provisional_owner": intake["integration"]["inbound_owner"],
                "basis": "adopter_intake.integration.inbound_owner",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "watch_policy_and_acceptance_configuration",
                "provisional_owner": "media_monitor_pilot_with_adopter_approval",
                "basis": "AP1 config boundary",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "provider_data_rights_and_permitted_use",
                "provisional_owner": human_decision(),
                "basis": "AP3 cannot infer legal rights",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "operator_review",
                "provisional_owner": intake["organization"]["primary_operator_role"],
                "basis": "adopter_intake.organization.primary_operator_role",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "real_editorial_approval",
                "provisional_owner": human_decision(),
                "basis": "AP4 explicit human authority",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "deployment_account",
                "provisional_owner": deployment_owner,
                "basis": "adopter_intake.privacy.deployment_account_owner when selected",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "recipient_address_and_contact_basis",
                "provisional_owner": "adopter",
                "basis": "AP5 deliberately does not invent recipient addresses",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "recipient_send_or_provider_operation",
                "provisional_owner": intake["integration"]["outbound_owner"],
                "basis": "adopter_intake.integration.outbound_owner",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "credentials_and_secret_rotation",
                "provisional_owner": human_decision(),
                "basis": "deployment/account ownership not inferred",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "support_incidents_and_service_levels",
                "provisional_owner": human_decision(),
                "basis": "AP6 reserved terms",
                "contractual_allocation": human_decision(),
            },
            {
                "area": "exit_export_retention_and_deletion",
                "provisional_owner": human_decision(),
                "basis": "must be selected for actual commercial path",
                "contractual_allocation": human_decision(),
            },
        ],
    }


def human_terms(intake: dict[str, Any], mode: str) -> dict[str, Any]:
    terms: dict[str, Any] = {
        "schema": TERMS_SCHEMA,
        "status": "human_completion_required_no_contract_formed",
        "transaction_mode": mode,
        "organization": intake["organization"]["name"],
    }
    terms.update({field: human_decision() for field in HUMAN_TERM_FIELDS})
    terms["agent_may_fill_these_terms"] = False
    terms["contract_formed"] = False
    terms["software_rights_granted"] = False
    terms["payment_obligation_created"] = False
    return terms


def asset_inventory(mode: str) -> dict[str, Any]:
    return {
        "schema": ASSET_SCHEMA,
        "status": "technical_inventory_for_scoping_no_rights_granted",
        "transaction_mode": mode,
        "technical_surfaces_available_for_scoping": [
            "ADOPT_MEDIA_MONITOR.md",
            "docs/adoption/",
            "contracts/schemas/",
            "scripts/",
            "apps/news_site/",
            ".github/workflows/",
            "examples/outlet/",
        ],
        "machine_readable_export_formats": ["JSON", "JSONL", "YAML", "HTML", "text"],
        "secrets_included_in_transfer_packet": False,
        "provider_credentials_included_in_transfer_packet": False,
        "software_or_source_code_grant": human_decision(),
        "deployment_asset_transfer": human_decision(),
        "historical_corpus_inclusion": human_decision(),
        "provider_account_transfer": human_decision(),
        "domain_or_dns_transfer": human_decision(),
        "post_transfer_support": human_decision(),
        "rights_granted_by_this_inventory": False,
    }


def scope_markdown(intake: dict[str, Any], mode: str) -> str:
    acceptance = intake["pilot_acceptance"]
    deliverables = intake["deliverables"]
    lines = [
        "# Media Monitor scope and acceptance seed",
        "",
        "> Status: scoping document only · no contract formed · no rights granted · no price agreed",
        "",
        f"- Organization: **{intake['organization']['name']}**",
        f"- Transaction mode under evaluation: `{mode}`",
        f"- Use case: `{intake['use_case']['class']}`",
        f"- Phase: `{intake['use_case']['phase']}`",
        f"- Source mode: `{intake['sources']['mode']}`",
        "",
        "## Requested operating shape",
        "",
        intake["use_case"]["summary"],
        "",
        "## Deliverables requested in intake",
        "",
    ]
    for deliverable in deliverables:
        lines.append(
            f"- `{deliverable['type']}` · cadence `{deliverable['cadence']}`"
            + (f" · window `{deliverable.get('delivery_window_local')}`" if deliverable.get("delivery_window_local") else "")
            + (f" · target items `{deliverable.get('target_item_count')}`" if deliverable.get("target_item_count") is not None else "")
        )
    lines.extend(
        [
            "",
            "## Acceptance criteria from intake",
            "",
            f"- pilot duration: **{acceptance['duration_days']} days**",
            f"- freshness target: **{acceptance['freshness_target_minutes']} minutes** (pilot acceptance target, not a contractual SLA until human terms say so)",
            f"- minimum successful scheduled cycles: **{acceptance['minimum_successful_scheduled_cycles']}**",
            f"- operator review must be exercised: **{str(acceptance['operator_review_exercised']).lower()}**",
            f"- recipient delivery must be exercised: **{str(acceptance['recipient_delivery_exercised']).lower()}**",
            f"- exclusions must be documented: **{str(acceptance['exclusions_documented']).lower()}**",
            "",
            "## Required governed evidence",
            "",
            "- completed validated adopter intake and hash",
            "- preview/production identity and source/input identity",
            "- operator review evidence where required",
            "- exact recipient artifact hashes and delivery evidence where required",
            "- deviations/bespoke interventions recorded before acceptance",
            "",
            "## Explicitly outside this scoping packet",
            "",
            "- price, currency, invoicing or payment obligation",
            "- repository/software license grant",
            "- source-code or deployment-asset transfer rights",
            "- privacy/DPA, warranty, indemnity, liability or governing-law terms",
            "- support hours, incident commitment or SLA",
            "- any signature or statement that a contract is already formed",
            "",
            "Those fields live in `human_terms.yaml` and must remain human decisions until explicitly completed and approved outside this agent-generated seed.",
            "",
        ]
    )
    return "\n".join(lines)


def exit_handoff_markdown(mode: str) -> str:
    return "\n".join(
        [
            "# Exit / handoff seed",
            "",
            "> Status: technical handoff checklist · contractual obligations are not defined here",
            "",
            f"Transaction mode under evaluation: `{mode}`",
            "",
            "## Technical surfaces that can be inventoried",
            "",
            "- adopter intake/configuration and hashes",
            "- validated contracts and schemas used by the adopter path",
            "- generated JSON/JSONL/YAML/HTML/text artifacts included by the eventual scope",
            "- deployment/configuration manifests included by the eventual scope",
            "- delivery/review evidence included by the eventual scope",
            "",
            "## Always excluded unless explicitly and safely transferred",
            "",
            "- secret values",
            "- provider credentials/tokens",
            "- unrelated adopter/customer data",
            "- unrelated repository/private operational state",
            "",
            "## Human decisions required before termination/transfer terms exist",
            "",
            "- exact export contents and cutoff time",
            "- historical corpus inclusion/exclusion",
            "- source-code/deployment-asset rights",
            "- provider/domain/account transfer",
            "- retention/deletion after termination",
            "- post-handoff support",
            "- acceptance/sign-off authority",
            "",
        ]
    )


def build_packet(intake_path: Path, out_dir: Path, *, replace: bool = False) -> dict[str, Any]:
    intake = load_intake(intake_path)
    require_valid(intake, load_schema())
    mode = transaction_mode(intake)

    if out_dir.exists():
        if not replace:
            raise ValueError(f"output already exists: {out_dir}; pass --replace to rebuild")
        import shutil

        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)

    responsibility = responsibility_matrix(intake, mode)
    terms = human_terms(intake, mode)
    assets = asset_inventory(mode)

    scope_path = out_dir / "scope_and_acceptance.md"
    responsibility_path = out_dir / "responsibility_matrix.yaml"
    terms_path = out_dir / "human_terms.yaml"
    assets_path = out_dir / "asset_inventory.yaml"
    handoff_path = out_dir / "exit_handoff.md"
    intake_copy = out_dir / "adopter_intake.yaml"

    atomic_write(scope_path, scope_markdown(intake, mode).encode("utf-8"))
    write_yaml(responsibility_path, responsibility)
    write_yaml(terms_path, terms)
    write_yaml(assets_path, assets)
    atomic_write(handoff_path, exit_handoff_markdown(mode).encode("utf-8"))
    atomic_write(intake_copy, yaml.safe_dump(intake, sort_keys=False, allow_unicode=True).encode("utf-8"))

    manifest = {
        "schema": PACKET_SCHEMA,
        "status": READY_STATUS,
        "transaction_mode": mode,
        "organization": intake["organization"]["name"],
        "source_intake_sha256": canonical_sha256(intake),
        "contract_formed": False,
        "software_rights_granted": False,
        "payment_obligation_created": False,
        "signatures_present": False,
        "human_terms_required": True,
        "files": {
            "scope_and_acceptance.md": sha256_file(scope_path),
            "responsibility_matrix.yaml": sha256_file(responsibility_path),
            "human_terms.yaml": sha256_file(terms_path),
            "asset_inventory.yaml": sha256_file(assets_path),
            "exit_handoff.md": sha256_file(handoff_path),
            "adopter_intake.yaml": sha256_file(intake_copy),
        },
        "next_human_action": "review scope, choose/approve reserved terms, then exchange the appropriate external commercial/legal document",
        "agent_authority": "may prepare and validate packet; may not fill reserved terms or represent acceptance/signature",
    }
    write_json(out_dir / "transaction_manifest.json", manifest)
    validate_packet(out_dir)
    return manifest


def validate_packet(out_dir: Path) -> dict[str, Any]:
    manifest = json.loads((out_dir / "transaction_manifest.json").read_text(encoding="utf-8"))
    terms = yaml.safe_load((out_dir / "human_terms.yaml").read_text(encoding="utf-8"))
    assets = yaml.safe_load((out_dir / "asset_inventory.yaml").read_text(encoding="utf-8"))
    responsibility = yaml.safe_load((out_dir / "responsibility_matrix.yaml").read_text(encoding="utf-8"))

    if manifest.get("schema") != PACKET_SCHEMA or manifest.get("status") != READY_STATUS:
        raise ValueError("invalid transaction manifest schema/status")
    for flag in ("contract_formed", "software_rights_granted", "payment_obligation_created", "signatures_present"):
        if manifest.get(flag) is not False:
            raise ValueError(f"transaction manifest may not set {flag}=true")
    if terms.get("schema") != TERMS_SCHEMA:
        raise ValueError("invalid human terms schema")
    for field in HUMAN_TERM_FIELDS:
        if terms.get(field) != human_decision():
            raise ValueError(f"human_terms.{field} must remain human_decision_required in agent-generated packet")
    if terms.get("contract_formed") is not False or terms.get("software_rights_granted") is not False:
        raise ValueError("human terms seed may not form contract or grant rights")
    if assets.get("schema") != ASSET_SCHEMA or assets.get("rights_granted_by_this_inventory") is not False:
        raise ValueError("asset inventory may not grant rights")
    for field in (
        "software_or_source_code_grant",
        "deployment_asset_transfer",
        "historical_corpus_inclusion",
        "provider_account_transfer",
        "domain_or_dns_transfer",
        "post_transfer_support",
    ):
        if assets.get(field) != human_decision():
            raise ValueError(f"asset_inventory.{field} must remain human_decision_required")
    if responsibility.get("schema") != RESPONSIBILITY_SCHEMA:
        raise ValueError("invalid responsibility matrix schema")
    for row in responsibility.get("rows") or []:
        if row.get("contractual_allocation") != human_decision():
            raise ValueError("responsibility matrix contractual allocations must remain human decisions")

    for filename, expected_sha in manifest.get("files", {}).items():
        path = out_dir / filename
        if not path.exists():
            raise ValueError(f"transaction packet file missing: {filename}")
        if sha256_file(path) != expected_sha:
            raise ValueError(f"transaction packet hash mismatch: {filename}")

    return {
        "schema": "media_monitor_transaction_packet_validation.v1",
        "status": "ok",
        "transaction_mode": manifest["transaction_mode"],
        "human_term_count": len(HUMAN_TERM_FIELDS),
        "file_count": len(manifest["files"]),
        "contract_formed": False,
        "software_rights_granted": False,
        "payment_obligation_created": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--intake", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--replace", action="store_true")
    validate = sub.add_parser("validate")
    validate.add_argument("--packet-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build_packet(args.intake, args.out, replace=args.replace)
        else:
            result = validate_packet(args.packet_dir)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
