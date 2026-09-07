#!/usr/bin/env python3
"""Evaluate Media Monitor first-adopter acceptance evidence without inventing it.

The evaluator is deliberately asymmetric:

- pending/not_accepted records may be evaluated at any time and receive an
  explicit missing-evidence report;
- accepted records must be real_external, complete, internally coherent, and
  explicitly confirmed with --confirm-real-external-evidence.

This tool never creates preview deployments, operator actions, deliveries,
commercial acceptance, signatures, or customer/adopter claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator

from scripts.adopter_intake import load_intake, load_schema as load_intake_schema, require_valid as require_valid_intake


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs" / "adoption" / "adopter_acceptance.schema.json"
REPORT_SCHEMA = "media_monitor_adopter_acceptance_evaluation.v1"
PLACEHOLDER = "human_evidence_required"
RESERVED_HOSTS = {"localhost", "127.0.0.1", "::1"}
RESERVED_SUFFIXES = (".invalid", ".test", ".example", ".example.com", ".example.org", ".example.net")


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected YAML object")
    return value


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def schema_errors(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(record), key=lambda exc: list(exc.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{path}: {error.message}")
    return errors


def require_schema_valid(record: dict[str, Any]) -> None:
    errors = schema_errors(record, load_schema())
    if errors:
        raise ValueError("invalid adopter acceptance record:\n- " + "\n- ".join(errors))


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    return not text or text.casefold().startswith(PLACEHOLDER)


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()) is not None


def is_real_preview_url(value: Any) -> bool:
    if is_placeholder(value) or not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.casefold()
    if host in RESERVED_HOSTS:
        return False
    if host in {"example.com", "example.org", "example.net"}:
        return False
    return not any(host.endswith(suffix) for suffix in RESERVED_SUFFIXES)


def evidence_ref_ready(value: Any) -> bool:
    return isinstance(value, str) and not is_placeholder(value)


def try_load_completed_intake(record: dict[str, Any], record_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    missing: list[str] = []
    intake_state = record["intake"]
    if not intake_state["completed"]:
        missing.append("intake.completed must be true")
        return None, missing
    if is_placeholder(intake_state["path"]):
        missing.append("intake.path requires real evidence")
        return None, missing
    intake_path = Path(str(intake_state["path"]))
    if not intake_path.is_absolute():
        intake_path = (record_path.parent / intake_path).resolve()
    if not intake_path.exists():
        missing.append(f"intake.path does not exist: {intake_path}")
        return None, missing
    try:
        intake = load_intake(intake_path)
        require_valid_intake(intake, load_intake_schema())
    except Exception as exc:
        missing.append(f"intake evidence is not a valid adopter intake: {exc}")
        return None, missing
    expected_sha = canonical_sha256(intake)
    if str(intake_state["sha256"]).casefold() != expected_sha.casefold():
        missing.append("intake.sha256 does not match the validated intake contents")
        return intake, missing
    return intake, missing


def acceptance_gaps(record: dict[str, Any], record_path: Path) -> tuple[list[str], dict[str, Any] | None]:
    gaps: list[str] = []

    if record["evidence_class"] != "real_external":
        gaps.append("evidence_class must be real_external")

    adopter = record["adopter"]
    if is_placeholder(adopter["organization"]):
        gaps.append("adopter.organization requires real evidence")
    if is_placeholder(adopter["adopter_ref"]):
        gaps.append("adopter.adopter_ref requires a non-placeholder external/internal reference")

    intake, intake_gaps = try_load_completed_intake(record, record_path)
    gaps.extend(intake_gaps)

    preview = record["preview"]
    if preview["status"] != "verified":
        gaps.append("preview.status must be verified")
    if not is_real_preview_url(preview["url"]):
        gaps.append("preview.url must be a real HTTPS non-placeholder/non-reserved URL")
    for field in ("site_id", "commit_sha", "evidence_ref"):
        if is_placeholder(preview[field]):
            gaps.append(f"preview.{field} requires real evidence")
    if preview["identity_verified"] is not True:
        gaps.append("preview.identity_verified must be true")
    if preview["owner_identity_leakage_absent"] is not True:
        gaps.append("preview.owner_identity_leakage_absent must be true")

    source = record["source"]
    if is_placeholder(source["mode"]):
        gaps.append("source.mode requires real evidence")
    if not evidence_ref_ready(source["evidence_ref"]):
        gaps.append("source.evidence_ref requires real evidence")
    if source["provider_rights_confirmed_by_human"] is not True:
        gaps.append("source.provider_rights_confirmed_by_human must be true")
    required_cycles = 1
    if intake is not None:
        required_cycles = int(intake["pilot_acceptance"]["minimum_successful_scheduled_cycles"])
    if int(source["repeated_successful_cycles"]) < required_cycles:
        gaps.append(
            f"source.repeated_successful_cycles must be >= intake minimum ({required_cycles})"
        )

    operator = record["operator"]
    if operator["non_developer_operator"] is not True:
        gaps.append("operator.non_developer_operator must be true")
    if operator["review_cycle_exercised"] is not True:
        gaps.append("operator.review_cycle_exercised must be true")
    if operator["no_storage_database_surgery"] is not True:
        gaps.append("operator.no_storage_database_surgery must be true")
    if not evidence_ref_ready(operator["evidence_ref"]):
        gaps.append("operator.evidence_ref requires real evidence")

    delivery = record["delivery"]
    if is_placeholder(delivery["deliverable_type"]):
        gaps.append("delivery.deliverable_type requires real evidence")
    if not is_sha256(delivery["artifact_sha256"]):
        gaps.append("delivery.artifact_sha256 must be a 64-hex SHA-256")
    if delivery["status"] != "delivered":
        gaps.append("delivery.status must be delivered")
    if is_placeholder(delivery["provider_message_ref"]):
        gaps.append("delivery.provider_message_ref requires provider/human evidence")
    if delivery["recipient_confirmed_useful"] is not True:
        gaps.append("delivery.recipient_confirmed_useful must be true")
    if not evidence_ref_ready(delivery["evidence_ref"]):
        gaps.append("delivery.evidence_ref requires real evidence")

    procurement = record["procurement"]
    if procurement["packet_reviewed_by_external_evaluator"] is not True:
        gaps.append("procurement.packet_reviewed_by_external_evaluator must be true")
    if procurement["unresolved_blockers"]:
        gaps.append("procurement.unresolved_blockers must be empty for accepted status")
    if not evidence_ref_ready(procurement["evidence_ref"]):
        gaps.append("procurement.evidence_ref requires real evidence")

    transaction = record["transaction"]
    if is_placeholder(transaction["commercial_path"]):
        gaps.append("transaction.commercial_path requires real evidence")
    if transaction["accepted_scope_or_contract"] is not True:
        gaps.append("transaction.accepted_scope_or_contract must be true")
    for field in ("external_document_ref", "owner_acceptance_ref", "counterparty_acceptance_ref"):
        if is_placeholder(transaction[field]):
            gaps.append(f"transaction.{field} requires real evidence")

    for index, deviation in enumerate(record["deviations"]):
        if deviation["status"] == "unresolved_blocking":
            gaps.append(f"deviations[{index}] is unresolved_blocking")
        if is_placeholder(deviation["evidence_ref"]):
            gaps.append(f"deviations[{index}].evidence_ref requires real evidence")

    acceptance = record["acceptance"]
    if acceptance["human_acceptance_recorded"] is not True:
        gaps.append("acceptance.human_acceptance_recorded must be true")
    for field in ("accepted_by", "accepted_at", "note"):
        if is_placeholder(acceptance[field]):
            gaps.append(f"acceptance.{field} requires real human evidence")

    return gaps, intake


def split_deviations(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reusable = [item for item in record["deviations"] if item["classification"] == "reusable_core"]
    adopter_specific = [item for item in record["deviations"] if item["classification"] == "adopter_specific"]
    return reusable, adopter_specific


def render_report(record: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        "# Media Monitor adopter acceptance evaluation",
        "",
        f"- Record status requested: `{record['status']}`",
        f"- Evidence class: `{record['evidence_class']}`",
        f"- Evaluation status: `{result['evaluation_status']}`",
        f"- Accepted: **{str(result['accepted']).lower()}**",
        "",
    ]
    if result["missing_for_acceptance"]:
        lines.extend(["## Missing / blocking evidence", ""])
        lines.extend(f"- {item}" for item in result["missing_for_acceptance"])
        lines.append("")
    else:
        lines.extend(["## Missing / blocking evidence", "", "- None.", ""])
    lines.extend(
        [
            "## Evidence rule",
            "",
            "This evaluator does not create any of the real-world evidence it checks. A pending record remains pending; an accepted record also requires explicit `--confirm-real-external-evidence` at evaluation time.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(record: dict[str, Any], result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "acceptance_report.md").write_text(render_report(record, result), encoding="utf-8")
    reusable, adopter_specific = split_deviations(record)
    (output_dir / "reusable_backlog.yaml").write_text(
        yaml.safe_dump({"schema": "media_monitor_adoption_reusable_backlog.v1", "items": reusable}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (output_dir / "adopter_specific_followups.yaml").write_text(
        yaml.safe_dump({"schema": "media_monitor_adopter_specific_followups.v1", "items": adopter_specific}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (output_dir / "acceptance_evaluation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def evaluate(
    record_path: Path,
    *,
    confirm_real_external_evidence: bool = False,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    record = load_yaml(record_path)
    require_schema_valid(record)
    gaps, intake = acceptance_gaps(record, record_path)

    requested_status = record["status"]
    accepted = False
    if requested_status == "accepted":
        if record["evidence_class"] != "real_external":
            raise ValueError("refusing accepted status unless evidence_class=real_external")
        if gaps:
            raise ValueError("refusing accepted status while real-adopter evidence is incomplete:\n- " + "\n- ".join(gaps))
        if not confirm_real_external_evidence:
            raise ValueError("refusing accepted status without --confirm-real-external-evidence")
        accepted = True
        evaluation_status = "accepted_real_external_evidence_confirmed"
    elif requested_status == "not_accepted":
        evaluation_status = "not_accepted"
    else:
        evaluation_status = "pending_real_adopter_evidence"

    result = {
        "schema": REPORT_SCHEMA,
        "evaluation_status": evaluation_status,
        "requested_status": requested_status,
        "evidence_class": record["evidence_class"],
        "accepted": accepted,
        "missing_for_acceptance": gaps,
        "missing_count": len(gaps),
        "intake_loaded": intake is not None,
        "record_sha256": canonical_sha256(record),
        "real_external_confirmation_used": bool(confirm_real_external_evidence and accepted),
        "customer_or_adopter_claim_allowed": accepted,
        "program_completion_allowed": accepted,
    }
    if output_dir is not None:
        write_outputs(record, result, output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--confirm-real-external-evidence", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(
            args.record,
            confirm_real_external_evidence=args.confirm_real_external_evidence,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
