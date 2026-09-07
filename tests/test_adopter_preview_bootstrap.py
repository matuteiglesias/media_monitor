import json
from pathlib import Path

from scripts.bootstrap_adopter_preview import PREVIEW_STATUS, build_preview


REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / "docs" / "adoption" / "adopter_intake.example.yaml"


def test_adopter_preview_builds_with_generic_compilers(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    manifest = build_preview(INTAKE, out)

    assert manifest["schema"] == "media_monitor_adopter_preview.v1"
    assert manifest["status"] == PREVIEW_STATUS
    assert manifest["deployment_status"] == "not_attempted"
    assert manifest["live_source_status"] == "not_attempted"
    assert manifest["customer_claim_allowed"] is False
    assert manifest["identity_isolation_check"] == "passed"
    assert manifest["signal_count"] >= 3
    assert manifest["curated_signal_count"] >= 3
    assert manifest["story_context_count"] >= 1

    snapshot = json.loads((out / "site_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["site"]["name"] == "Example Intelligence Desk"
    assert snapshot["site"]["locale"] == "es-AR"

    encoded = json.dumps(snapshot, ensure_ascii=False).casefold()
    assert "matías iglesias" not in encoded
    assert "matias iglesias" not in encoded
    assert "análisis económico de argentina" not in encoded


def test_adopter_preview_is_deterministic_when_rebuilt_in_same_workspace(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    first = build_preview(INTAKE, out)
    first_snapshot = (out / "site_snapshot.json").read_bytes()

    second = build_preview(INTAKE, out, replace=True)
    second_snapshot = (out / "site_snapshot.json").read_bytes()

    assert first["site_id"] == second["site_id"]
    assert first["source_intake_sha256"] == second["source_intake_sha256"]
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first_snapshot == second_snapshot


def test_preview_identity_is_intake_stable_but_snapshot_provenance_is_workspace_bound(tmp_path: Path) -> None:
    first = build_preview(INTAKE, tmp_path / "first")
    second = build_preview(INTAKE, tmp_path / "second")

    # AP2 owns an intake-derived adopter identity. site_snapshot.v4 separately
    # records source paths in provenance, so relocating the canonical workspace
    # is allowed to change snapshot_id without changing adopter identity.
    assert first["site_id"] == second["site_id"]
    assert first["source_intake_sha256"] == second["source_intake_sha256"]


def test_adopter_preview_package_carries_plan_and_caveat(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    manifest = build_preview(INTAKE, out)
    plan = json.loads((out / "implementation_plan.json").read_text(encoding="utf-8"))
    readme = (out / "README.txt").read_text(encoding="utf-8")

    assert plan["source_intake_sha256"] == manifest["source_intake_sha256"]
    assert "AP3" in plan["suggested_packet_order"]
    assert "not live news" in readme.lower()
    assert "not a deployed customer instance" in readme.lower()
