from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NEWS_SITE_ROOT = REPO_ROOT / "apps" / "news_site"


def test_publish_script_npm_commands_are_owned_by_news_site() -> None:
    package = json.loads((NEWS_SITE_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    expected = {
        "refresh-data": "node scripts/refresh_public_data.mjs",
        "smoke:public-data": "node scripts/validate_public_data.mjs",
    }

    for name, command in expected.items():
        assert scripts.get(name) == command
        script_path = NEWS_SITE_ROOT / command.removeprefix("node ")
        assert script_path.is_file(), f"{name} points to missing file: {script_path}"


def test_shell_publisher_only_invokes_declared_news_site_scripts() -> None:
    package = json.loads((NEWS_SITE_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]
    publisher = (REPO_ROOT / "scripts" / "publish_news_site.sh").read_text(
        encoding="utf-8"
    )

    invoked = {"refresh-data", "smoke:public-data"}
    for name in invoked:
        assert f"run {name}" in publisher or f"run --silent {name}" in publisher
        assert name in scripts


def test_freshness_notice_is_global_and_request_time() -> None:
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")
    route = (NEWS_SITE_ROOT / "app" / "api" / "health" / "route.ts").read_text(
        encoding="utf-8"
    )

    assert 'export const dynamic = "force-dynamic"' in layout
    assert "<FreshnessNotice />" in layout
    assert "buildPublicationHealth" in route
    assert '"Cache-Control": "no-store"' in route
