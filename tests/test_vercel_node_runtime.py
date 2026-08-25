import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_news_site_pins_supported_vercel_node_major():
    package = json.loads((ROOT / "apps/news_site/package.json").read_text(encoding="utf-8"))
    assert package.get("engines", {}).get("node") == "22.x"


def test_runtime_ci_uses_compatible_node_major():
    workflow = (ROOT / ".github/workflows/runtime-ci.yml").read_text(encoding="utf-8")
    assert 'node-version: "20"' in workflow or 'node-version: "22"' in workflow
