from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
import pandas as pd

sys.modules.setdefault("psycopg", types.SimpleNamespace(connect=lambda *_a, **_k: None))
sys.modules.setdefault("feedparser", types.SimpleNamespace(parse=lambda *_a, **_k: None))

from apps.news_acquire.src.news_acquire.feed_config import load_feed_config
from apps.news_acquire.src.news_acquire.runtime import SensingControls
from apps.news_acquire.src.news_acquire import stage01_digests as stage01


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("ACQUIRE_NETWORK", "0", (False, True, True, False)),
        ("WRITE_ARTIFACTS", "0", (True, False, True, False)),
        ("ENQUEUE_SCRAPE", "0", (True, True, False, False)),
        ("DB_RUN_BOOKKEEPING", "1", (True, True, True, True)),
    ],
)
def test_each_sensing_control_is_independent(monkeypatch, name, value, expected) -> None:
    for variable in (
        "DRY_RUN",
        "ACQUIRE_NETWORK",
        "WRITE_ARTIFACTS",
        "ENQUEUE_SCRAPE",
        "DB_RUN_BOOKKEEPING",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(name, value)

    controls = SensingControls.from_env()

    assert (
        controls.acquire_network,
        controls.write_artifacts,
        controls.enqueue_scrape,
        controls.db_run_bookkeeping,
    ) == expected


def test_dry_run_remains_a_compatibility_alias(monkeypatch) -> None:
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.delenv("ACQUIRE_NETWORK", raising=False)
    monkeypatch.delenv("WRITE_ARTIFACTS", raising=False)
    monkeypatch.delenv("ENQUEUE_SCRAPE", raising=False)
    monkeypatch.delenv("DB_RUN_BOOKKEEPING", raising=False)

    assert SensingControls.from_env() == SensingControls(False, True, False, False)


def test_explicit_control_overrides_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.setenv("ACQUIRE_NETWORK", "1")
    monkeypatch.setenv("ENQUEUE_SCRAPE", "1")

    controls = SensingControls.from_env()

    assert controls.acquire_network is True
    assert controls.enqueue_scrape is True


def test_default_feed_configuration_preserves_all_topics() -> None:
    feeds = load_feed_config()

    assert len(feeds) == 7
    assert "Inflación y Precios" in feeds
    assert "Personajes Políticos y Económicos" in feeds


@pytest.mark.parametrize(
    "payload",
    [
        "schema_version: sensing_feeds.v0\nfeeds: []\n",
        "schema_version: sensing_feeds.v1\nfeeds: []\n",
        "schema_version: sensing_feeds.v1\nfeeds:\n  - topic: test\n    url: file:///tmp/feed\n",
    ],
)
def test_invalid_feed_configuration_fails_closed(tmp_path: Path, payload: str) -> None:
    config = tmp_path / "feeds.yaml"
    config.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="invalid sensing feed config"):
        load_feed_config(config)


def test_enqueue_can_run_without_artifact_writes(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    queued: list[tuple] = []
    monkeypatch.setenv("DIGEST_AT", "20250101T00")
    monkeypatch.setenv("ACQUIRE_NETWORK", "1")
    monkeypatch.setenv("WRITE_ARTIFACTS", "0")
    monkeypatch.setenv("ENQUEUE_SCRAPE", "1")
    monkeypatch.setenv("DB_RUN_BOOKKEEPING", "0")
    monkeypatch.setattr(stage01, "DATA_DIR", data_dir)
    monkeypatch.setattr(stage01, "SLICE_DIR", data_dir / "rss_slices")
    monkeypatch.setattr(stage01, "RSS_DUMPS_DIR", data_dir / "rss_slices" / "rss_dumps")
    monkeypatch.setattr(stage01, "JSONL_DIR", data_dir / "slices" / "jsonl")
    monkeypatch.setattr(stage01, "QUAR_DIR", data_dir / "quarantine")
    monkeypatch.setattr(stage01, "load_feed_config", lambda: {"topic": "https://example.test/rss"})
    monkeypatch.setattr(
        stage01,
        "fetch_rss_now",
        lambda *_a, **_k: pd.DataFrame(
            [
                {
                    "uid": "uid",
                    "Topic": "topic",
                    "Title": "headline",
                    "Link": "https://example.test/article",
                    "Published": pd.Timestamp("2025-01-01T00:30:00Z"),
                    "Source": "source",
                }
            ]
        ),
    )
    monkeypatch.setattr(stage01.db, "push_work", lambda *args: queued.append(args))

    assert stage01.run() == 0
    assert len(queued) == 1
    assert queued[0][0] == "scrape"
    assert not data_dir.exists()


def test_enabled_db_bookkeeping_error_is_not_suppressed(monkeypatch) -> None:
    monkeypatch.setenv("DIGEST_AT", "20250101T00")
    monkeypatch.setenv("ACQUIRE_NETWORK", "0")
    monkeypatch.setenv("WRITE_ARTIFACTS", "0")
    monkeypatch.setenv("ENQUEUE_SCRAPE", "0")
    monkeypatch.setenv("DB_RUN_BOOKKEEPING", "1")
    monkeypatch.setattr(stage01, "load_feed_config", lambda: {"topic": "https://example.test/rss"})
    monkeypatch.setattr(
        stage01.db,
        "start_run",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("bookkeeping unavailable")),
    )

    with pytest.raises(RuntimeError, match="bookkeeping unavailable"):
        stage01.run()


def test_acquisition_failure_finishes_enabled_bookkeeping(monkeypatch) -> None:
    events: list[tuple[str, tuple, dict]] = []
    monkeypatch.setenv("DIGEST_AT", "20250101T00")
    monkeypatch.setenv("ACQUIRE_NETWORK", "1")
    monkeypatch.setenv("WRITE_ARTIFACTS", "0")
    monkeypatch.setenv("ENQUEUE_SCRAPE", "0")
    monkeypatch.setenv("DB_RUN_BOOKKEEPING", "1")
    monkeypatch.setattr(stage01, "load_feed_config", lambda: {"topic": "https://example.test/rss"})
    monkeypatch.setattr(
        stage01,
        "fetch_rss_now",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("feed unavailable")),
    )
    monkeypatch.setattr(
        stage01.db,
        "start_run",
        lambda *args, **kwargs: events.append(("start", args, kwargs)),
    )
    monkeypatch.setattr(
        stage01.db,
        "finish_run",
        lambda *args, **kwargs: events.append(("finish", args, kwargs)),
    )

    with pytest.raises(RuntimeError, match="feed unavailable"):
        stage01.run()

    assert [event[0] for event in events] == ["start", "finish"]
    assert events[1][2]["ok"] == 0
    assert events[1][2]["fail"] == 1
    assert "feed unavailable" in events[1][2]["meta"]["error"]


def test_wrapper_can_leave_lane_status_to_orchestrator(tmp_path: Path) -> None:
    telemetry = tmp_path / "observability"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_with_run_record.py"),
            "--project-id",
            "media_monitor",
            "--lane",
            "sensing",
            "--stage",
            "s01",
            "--telemetry-root",
            str(telemetry),
            "--no-lane-status",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    record = json.loads((telemetry / "run_records.jsonl").read_text().strip())
    assert record["status"] == "success"
    assert not (telemetry / "status" / "sensing_latest.json").exists()
    assert not (telemetry / "status" / "summary.json").exists()


def test_compatibility_command_still_accepts_dry_run() -> None:
    env = {**os.environ, "DRY_RUN": "1", "DIGEST_AT": "20250101T00"}
    result = subprocess.run(
        ["bash", "bin/run_minimal_loop_once.sh", "--help"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "DRY_RUN=0|1" in result.stdout
    assert "ACQUIRE_NETWORK=0|1" in result.stdout
