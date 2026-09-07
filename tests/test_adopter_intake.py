import copy
import json
from pathlib import Path

import yaml

from scripts.adopter_intake import compile_plan, load_schema, require_valid, validation_errors


REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "docs" / "adoption" / "adopter_intake.example.yaml"
SCHEMA = REPO / "docs" / "adoption" / "adopter_intake.schema.json"


def _example():
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def test_example_adopter_intake_validates() -> None:
    intake = _example()
    require_valid(intake, load_schema(SCHEMA))


def test_generated_text_cannot_be_auto_published() -> None:
    intake = _example()
    intake["editorial_authority"]["auto_publish_generated_text"] = True
    errors = validation_errors(intake, load_schema(SCHEMA))
    assert any("auto_publish_generated_text" in error for error in errors)


def test_plan_classifies_external_feed_private_delivery_and_human_decisions() -> None:
    intake = _example()
    plan = compile_plan(intake)

    assert plan["schema"] == "media_monitor_adopter_plan.v1"
    assert len(plan["source_intake_sha256"]) == 64

    adapter_areas = {item["area"] for item in plan["classifications"]["ADAPTER_REQUIRED"]}
    assert "sources" in adapter_areas

    reusable = {item["area"] for item in plan["classifications"]["REUSABLE_PLATFORM_REQUIREMENT"]}
    assert "deliverables[0]" in reusable
    assert "privacy.mode" in reusable

    human = {item["area"] for item in plan["classifications"]["HUMAN_DECISION_REQUIRED"]}
    assert "commercial_path.price" in human
    assert "commercial_path.license_terms" in human
    assert "identity.attribution" in human

    assert plan["classifications"]["OUT_OF_SCOPE"] == []
    assert plan["suggested_packet_order"] == ["AP3", "AP5", "AP4", "AP2"]


def test_plan_hash_is_deterministic_and_sensitive_to_intake() -> None:
    intake = _example()
    first = compile_plan(intake)["source_intake_sha256"]
    second = compile_plan(copy.deepcopy(intake))["source_intake_sha256"]
    assert first == second

    changed = copy.deepcopy(intake)
    changed["watch_policy"]["topics"].append("energy")
    assert compile_plan(changed)["source_intake_sha256"] != first


def test_schema_is_valid_json_schema_object() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema"]["const"] == "media_monitor_adopter_intake.v1"
