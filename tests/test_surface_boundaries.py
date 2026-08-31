from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_system_declares_distinct_media_monitor_surfaces() -> None:
    system = yaml.safe_load((REPO / "SYSTEM.yaml").read_text(encoding="utf-8"))
    assert system["naming"]["repository_slug"] == "media_monitor"
    assert system["naming"]["system_id"] == "media-monitor"

    surfaces = system["surfaces"]
    assert surfaces["system_documentation"]["path"] == "docs-site"
    assert surfaces["argentina_outlet"]["path"] == "apps/news_site"
    assert surfaces["operator_last_mile"]["path"] == "web"
    assert surfaces["channel_monitor"]["path"] == "apps/channel_monitor"

    ids = [surface["surface_id"] for surface in surfaces.values()]
    assert len(ids) == len(set(ids))
    assert surfaces["argentina_outlet"]["status"] == "incubated-in-repository"
    assert surfaces["argentina_outlet"]["instance_config"] == "sites/argentina-general.json"


def test_declared_surface_roots_exist_and_are_not_collapsed() -> None:
    system = yaml.safe_load((REPO / "SYSTEM.yaml").read_text(encoding="utf-8"))
    paths = [surface["path"] for surface in system["surfaces"].values()]
    assert len(paths) == len(set(paths))
    for path in paths:
        assert (REPO / path).exists(), path


def test_root_vercel_surface_is_operator_last_mile_not_the_outlet() -> None:
    config = _json("vercel.json")
    rewrites = config.get("rewrites", [])
    assert {"source": "/", "destination": "/web/index.html"} in rewrites
    assert (REPO / "web/index.html").exists()
    assert (REPO / "apps/news_site").is_dir()
    assert (REPO / "docs-site").is_dir()
