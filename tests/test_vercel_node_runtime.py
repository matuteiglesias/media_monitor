import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_news_site_pins_supported_vercel_node_major():
    package = json.loads((ROOT / "apps/news_site/package.json").read_text(encoding="utf-8"))
    assert package.get("engines", {}).get("node") == "22.x"


def test_runtime_ci_uses_compatible_node_major():
    workflow = (ROOT / ".github/workflows/runtime-ci.yml").read_text(encoding="utf-8")
    assert 'node-version: "20"' in workflow or 'node-version: "22"' in workflow


def test_scheduled_publication_pins_vercel_cli():
    workflow = (ROOT / ".github/workflows/scheduled-publication.yml").read_text(encoding="utf-8")
    assert 'VERCEL_CLI_VERSION: "59.11.7"' in workflow
    assert 'vercel@${VERCEL_CLI_VERSION}' in workflow
    assert "vercel@latest" not in workflow
