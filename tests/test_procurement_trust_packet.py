from pathlib import Path

import pytest
import yaml

from scripts.validate_procurement_trust import DEFAULT_PACKET, validate_packet


def _copy_packet(tmp_path: Path) -> tuple[Path, dict]:
    payload = yaml.safe_load(DEFAULT_PACKET.read_text(encoding="utf-8"))
    path = tmp_path / "procurement_trust_state.yaml"
    return path, payload


def _write(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_current_procurement_packet_validates_against_repository_evidence() -> None:
    result = validate_packet(DEFAULT_PACKET)

    assert result["status"] == "ok"
    assert result["human_decision_count"] >= 20
    assert result["repository_license_files"] == []
    assert result["python_direct_pin_count"] >= 5
    assert result["scheduled_node_version"] == "20"
    assert result["news_site_node_engine"] == "22.x"
    assert result["node_runtime_contract_status"] == "mismatch_open"
    assert result["publication_evidence_retention_days"] == 14
    assert result["contractual_sla_claimed"] is False
    assert result["certifications_claimed"] is False


def test_packet_cannot_silently_choose_repository_license(tmp_path: Path) -> None:
    path, payload = _copy_packet(tmp_path)
    payload["repository"]["repository_level_license"]["decision"] = "MIT"
    _write(path, payload)

    with pytest.raises(ValueError, match="human_decision_required"):
        validate_packet(path)


def test_packet_cannot_hide_known_node_runtime_mismatch(tmp_path: Path) -> None:
    path, payload = _copy_packet(tmp_path)
    payload["runtime_and_deployment"]["node_runtime_contract_status"] = "aligned"
    _write(path, payload)

    with pytest.raises(ValueError, match="Node runtime mismatch"):
        validate_packet(path)


def test_implementation_freshness_target_cannot_be_recast_as_sla(tmp_path: Path) -> None:
    path, payload = _copy_packet(tmp_path)
    payload["runtime_and_deployment"]["public_freshness_is_contractual_sla"] = True
    _write(path, payload)

    with pytest.raises(ValueError, match="contractual SLA"):
        validate_packet(path)


def test_packet_fails_when_evidence_pointer_does_not_exist(tmp_path: Path) -> None:
    path, payload = _copy_packet(tmp_path)
    payload["evidence_paths"].append("docs/adoption/does-not-exist.md")
    _write(path, payload)

    with pytest.raises(ValueError, match="evidence paths missing"):
        validate_packet(path)
