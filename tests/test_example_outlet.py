from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "outlet"


def load_builder():
    spec = importlib.util.spec_from_file_location("example_outlet_build", EXAMPLE / "build.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_outlet_builds_through_generic_compilers(tmp_path: Path) -> None:
    module = load_builder()
    first = module.build(tmp_path / "outlet")
    snapshot = json.loads((tmp_path / "outlet/site_snapshot.json").read_text(encoding="utf-8"))
    second = module.build(tmp_path / "outlet")

    assert first["snapshot_id"] == second["snapshot_id"]
    assert snapshot["schema_name"] == "site_snapshot.v4"
    assert snapshot["site"]["site_id"] == "example-general"
    assert snapshot["site"]["name"] == "Example Economic Monitor"
    assert first["selection_policy_id"] == "example-general-v1"
    assert first["signal_count"] == 4
    assert first["curated_signal_count"] == 4
    assert first["story_context_count"] == 4
    assert {row["topic"] for row in snapshot["signals"]["latest"]} == {"Prices", "Labor", "Trade"}


def test_example_outlet_is_configuration_not_core_special_case() -> None:
    builder = (EXAMPLE / "build.py").read_text(encoding="utf-8")
    tutorial = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    selection_core = (ROOT / "scripts/build_editorial_selection.py").read_text(encoding="utf-8")
    snapshot_core = (ROOT / "scripts/build_site_snapshot.py").read_text(encoding="utf-8")

    assert "build_editorial_selection" in builder
    assert "build_story_contexts" in builder
    assert "build_site_snapshot" in builder
    assert "without editing `apps/**` or the core Python builders" in tutorial
    assert "What should not change" in tutorial
    for outlet_specific in ("Example Economic Monitor", "example-general-v1"):
        assert outlet_specific not in selection_core
        assert outlet_specific not in snapshot_core
