import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from apps.news_acquire.src.news_acquire import stage01_digests as stage01
from apps.news_acquire.src.news_acquire import stage02_master_index_update as stage02


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_story_contexts import unique_refs
from roll_site import Result, call


def test_recent_sensing_window_covers_configured_editorial_freshness_horizon():
    policy = json.loads((ROOT / "config/editorial_selection.argentina.json").read_text(encoding="utf-8"))
    horizon = timedelta(minutes=policy["max_age_minutes"])
    hour = datetime(2026, 8, 25, 2, 0, tzinfo=timezone.utc)
    slices = {label: (start, end) for label, start, end in stage01.compute_slices(hour)}

    assert "1h_window" in slices
    assert "recent_4h_window" in slices
    start, end = slices["recent_4h_window"]
    assert start == hour - timedelta(hours=3)
    assert end == hour + timedelta(hours=1)

    # A refresh can happen anywhere inside the UTC hour. The sensing window must
    # still reach behind the selector's full freshness cutoff at minute 00 or 59.
    for minute in (0, 23, 59):
        as_of = hour + timedelta(minutes=minute)
        assert start <= as_of - horizon
        assert end > as_of


def _raw_row(topic="Inflación y Precios"):
    return {
        "digest_file": "recent_4h_window_20260825T0200",
        "window_type": "recent_4h_window",
        "article_id": 1,
        "Title": "IPC: nueva señal",
        "Source": "Fuente",
        "Link": "https://example.com/ipc",
        "Published": "2026-08-25T01:45:00Z",
        "index_id": "IDX1",
        "Topic": topic,
    }


def test_stage02_preserves_topic_in_digest_map(tmp_path, monkeypatch):
    raw = pd.DataFrame([_raw_row()])
    good, bad = stage02.validate_input_df(raw, "test", write_artifacts=False)
    assert bad == 0
    assert good.loc[0, "Topic"] == "Inflación y Precios"

    monkeypatch.setattr(stage02, "DATA_DIR", tmp_path)
    monkeypatch.setattr(stage02, "DIGEST_MAP_DIR", tmp_path / "digest_map")
    path = stage02.write_digest_map_csv(good, "20260825T02", null_sink=False)
    written = pd.read_csv(path)
    assert "Topic" in written.columns
    assert written.loc[0, "Topic"] == "Inflación y Precios"


def test_stage02_compatibility_defaults_missing_topic_without_dropping_row():
    raw = pd.DataFrame([{key: value for key, value in _raw_row().items() if key != "Topic"}])
    good, bad = stage02.validate_input_df(raw, "test", write_artifacts=False)
    assert bad == 0
    assert good.loc[0, "Topic"] == "All Topics"


def test_overlapping_sensing_windows_create_one_story_context_identity():
    base = {
        "digest_at": "20260825T02",
        "index_id": "IDX1",
        "title": "IPC: nueva señal",
        "source": "Fuente",
        "published_at": "2026-08-25T01:45:00Z",
        "topic": "Inflación y Precios",
        "link": "https://example.com/ipc",
    }
    rows = [base | {"window_type": "1h_window"}, base | {"window_type": "recent_4h_window"}]
    assert unique_refs(rows) == [rows[0]]


def test_repo_controlled_selector_failure_surfaces_actionable_reason(tmp_path):
    def runner(command, *, cwd, env=None):
        return Result(
            command,
            1,
            "[editorial-selection] ERROR: selected 2 signals; minimum_items=5\n",
            "",
        )

    with pytest.raises(RuntimeError, match=r"selected 2 signals; minimum_items=5"):
        call(
            runner,
            ["python", "scripts/build_editorial_selection.py"],
            tmp_path,
            stage="editorial-selection",
            expose_output=True,
        )


def test_provider_output_remains_hidden_by_default(tmp_path):
    def runner(command, *, cwd, env=None):
        return Result(command, 1, "token=do-not-leak", "")

    with pytest.raises(RuntimeError) as exc:
        call(runner, ["vercel", "deploy"], tmp_path, stage="deploy")
    assert "do-not-leak" not in str(exc.value)
