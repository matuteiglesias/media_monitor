#!/usr/bin/env python3
"""Validate a Media Monitor adopter intake and compile a bounded implementation plan.

This is adoption-program tooling, not a runtime owner. It does not provision,
deploy, price, license, or mutate production state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO / "docs" / "adoption" / "adopter_intake.schema.json"
PLAN_SCHEMA = "media_monitor_adopter_plan.v1"


class IntakeError(RuntimeError):
    pass


def load_intake(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise IntakeError("intake must decode to an object")
    return data


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise IntakeError("schema must decode to an object")
    return data


def validation_errors(intake: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(intake), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{path}: {error.message}")
    return errors


def require_valid(intake: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = validation_errors(intake, schema)
    if errors:
        raise IntakeError("invalid adopter intake:\n- " + "\n- ".join(errors))


def _canonical_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _item(area: str, reason: str, packet: str | None = None) -> dict[str, str]:
    item = {"area": area, "reason": reason}
    if packet:
        item["suggested_packet"] = packet
    return item


def compile_plan(intake: dict[str, Any]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, str]]] = {
        "CONFIG_ONLY": [],
        "ADAPTER_REQUIRED": [],
        "REUSABLE_PLATFORM_REQUIREMENT": [],
        "HUMAN_DECISION_REQUIRED": [],
        "OUT_OF_SCOPE": [],
    }
    questions: list[str] = []

    buckets["CONFIG_ONLY"].extend(
        [
            _item("watch_policy", "topics, geography, languages, freshness and exclusions belong in adopter configuration"),
            _item("identity", "name, locale and preview identity are adopter configuration unless a new generic presentation capability is requested"),
            _item("editorial_authority", "human-review and evidence-link policy map to existing governed authority semantics"),
            _item("pilot_acceptance", "duration, freshness target and required successful cycles are acceptance configuration"),
        ]
    )

    source = intake["sources"]
    source_mode = source["mode"]
    if source_mode in {"adopter_provided_files", "adopter_provided_feed", "adopter_provider_api", "mixed"}:
        buckets["ADAPTER_REQUIRED"].append(
            _item(
                "sources",
                f"source mode {source_mode!r} requires a governed import seam rather than adopter-specific edits to news_acquire",
                "AP3",
            )
        )
    elif source_mode == "undecided":
        buckets["HUMAN_DECISION_REQUIRED"].append(
            _item("sources.mode", "source ownership/interface must be chosen before preview implementation", "AP1")
        )
        questions.append("Choose whether Media Monitor acquires public feeds or consumes adopter/provider signals.")

    for field in ("interface", "authentication", "retention_constraints"):
        value = str(source.get(field, "")).strip().lower()
        if value in {"", "to_be_defined", "undecided", "unknown"}:
            buckets["HUMAN_DECISION_REQUIRED"].append(
                _item(f"sources.{field}", "external-source boundary is not yet specified", "AP1/AP3")
            )

    current_deliverables = {"web_outlet"}
    for index, deliverable in enumerate(intake["deliverables"]):
        dtype = deliverable["type"]
        if dtype not in current_deliverables:
            buckets["REUSABLE_PLATFORM_REQUIREMENT"].append(
                _item(
                    f"deliverables[{index}]",
                    f"{dtype!r} is a recipient-facing delivery surface to be earned as reusable AP5 work",
                    "AP5",
                )
            )

    privacy = intake["privacy"]
    if privacy["mode"] in {"private", "mixed"}:
        buckets["REUSABLE_PLATFORM_REQUIREMENT"].append(
            _item(
                "privacy.mode",
                "private/mixed adopter operation needs an explicit access-control/operator boundary rather than assuming the public outlet model",
                "AP4/AP6",
            )
        )
    auth_value = str(privacy.get("authentication", "")).strip().lower()
    if auth_value in {"", "to_be_defined", "pilot_level_to_be_defined", "undecided", "unknown"}:
        buckets["HUMAN_DECISION_REQUIRED"].append(
            _item("privacy.authentication", "required authentication posture is not yet chosen", "AP4/AP6")
        )
    if privacy.get("deployment_account_owner") == "undecided":
        buckets["HUMAN_DECISION_REQUIRED"].append(
            _item("privacy.deployment_account_owner", "deployment-account ownership is a responsibility decision", "AP6")
        )

    identity = intake["identity"]
    if identity.get("attribution") == "to_be_decided":
        buckets["HUMAN_DECISION_REQUIRED"].append(
            _item("identity.attribution", "white-label attribution is a commercial/brand decision", "AP6/AP7")
        )

    commercial = intake["commercial_path"]
    buckets["HUMAN_DECISION_REQUIRED"].extend(
        [
            _item("commercial_path.price", "pricing is reserved for the human owner", "AP7"),
            _item("commercial_path.license_terms", "software/license rights are reserved for explicit human/legal decision", "AP6/AP7"),
        ]
    )

    if intake["editorial_authority"]["auto_publish_generated_text"] is not False:
        buckets["OUT_OF_SCOPE"].append(
            _item(
                "editorial_authority.auto_publish_generated_text",
                "seed adoption work may not collapse generated content into approved/published content",
            )
        )

    if not questions and buckets["HUMAN_DECISION_REQUIRED"]:
        questions.append("Resolve the HUMAN_DECISION_REQUIRED items before implementation where they block the selected pilot path.")

    next_packets: list[str] = []
    if buckets["ADAPTER_REQUIRED"]:
        next_packets.append("AP3")
    if any(item.get("suggested_packet") == "AP5" for item in buckets["REUSABLE_PLATFORM_REQUIREMENT"]):
        next_packets.append("AP5")
    if privacy["mode"] in {"private", "mixed"}:
        next_packets.append("AP4")
    next_packets.append("AP2")
    next_packets = list(dict.fromkeys(next_packets))

    return {
        "schema": PLAN_SCHEMA,
        "source_intake_schema": intake["schema"],
        "source_intake_sha256": _canonical_sha256(intake),
        "organization": intake["organization"]["name"],
        "use_case_class": intake["use_case"]["class"],
        "phase": intake["use_case"]["phase"],
        "commercial_path_under_evaluation": commercial["evaluating"],
        "classifications": buckets,
        "blocking_questions": questions,
        "suggested_packet_order": next_packets,
        "guardrails": [
            "no adopter-specific conditionals in generic core builders",
            "generated != approved != published",
            "no pricing or license terms inferred by this tool",
            "plan output is advisory and requires human activation before implementation",
        ],
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Media Monitor adopter implementation plan",
        "",
        f"- Organization: **{plan['organization']}**",
        f"- Use case: `{plan['use_case_class']}`",
        f"- Phase: `{plan['phase']}`",
        f"- Intake SHA-256: `{plan['source_intake_sha256']}`",
        "",
    ]
    for bucket, items in plan["classifications"].items():
        lines.extend([f"## {bucket}", ""])
        if not items:
            lines.append("- None identified by the deterministic classifier.")
        else:
            for item in items:
                packet = f" — `{item['suggested_packet']}`" if item.get("suggested_packet") else ""
                lines.append(f"- **{item['area']}**: {item['reason']}{packet}")
        lines.append("")
    lines.extend(["## Suggested packet order", "", " → ".join(plan["suggested_packet_order"]), ""])
    if plan["blocking_questions"]:
        lines.extend(["## Blocking questions", ""])
        lines.extend(f"- {question}" for question in plan["blocking_questions"])
        lines.append("")
    lines.extend(["## Guardrails", ""])
    lines.extend(f"- {rule}" for rule in plan["guardrails"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--plan", action="store_true", help="compile the validated intake into an implementation plan")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        intake = load_intake(args.intake)
        schema = load_schema(args.schema)
        require_valid(intake, schema)
        if args.plan:
            result: Any = compile_plan(intake)
            payload = render_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        else:
            payload = json.dumps({"status": "valid", "schema": intake["schema"], "sha256": _canonical_sha256(intake)}, indent=2) + "\n"
    except (OSError, ValueError, yaml.YAMLError, IntakeError) as exc:
        parser.exit(2, f"error: {exc}\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
