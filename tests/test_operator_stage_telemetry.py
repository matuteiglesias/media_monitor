import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from error_surface import wrapped_stage_timeline
from media_refresh import refresh
from roll_site import Result, roll


def _snapshot(root: Path, digest: str = "20260825T02") -> None:
    path = root / "apps/news_site/public/data/site_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_name": "site_snapshot.v4",
                "site": {"site_id": "argentina-general"},
                "digest_at": digest,
                "snapshot_id": "a" * 64,
                "metrics": {
                    "item_count": 12,
                    "section_count": 3,
                    "published_article_count": 0,
                    "curated_signal_count": 6,
                    "story_context_count": 12,
                },
            }
        ),
        encoding="utf-8",
    )


class BuildFailureRunner:
    def __init__(self, root: Path):
        self.root = root

    def __call__(self, command, *, cwd, env=None):
        if command[:2] == ["vercel", "build"]:
            return Result(
                command,
                1,
                "Vercel CLI\n",
                "Error: Could not locate the Next.js project root\ntoken=super-secret-value\n",
            )
        return Result(command, 0, "", "")


def test_roll_persists_stage_timeline_and_redacted_build_log(tmp_path):
    _snapshot(tmp_path)
    record, code = roll(
        "argentina-general",
        "20260825T02",
        "preview",
        tmp_path,
        runner=BuildFailureRunner(tmp_path),
        sleep=lambda _: None,
    )
    assert code == 1
    assert record["failed_stage"] == "build"
    stages = record["stages"]
    assert [row["stage"] for row in stages[:8]] == [
        "publication-index",
        "editorial-selection",
        "story-contexts",
        "compile",
        "validate",
        "identity",
        "pull",
        "build",
    ]
    assert all(isinstance(row["duration_ms"], int) and row["duration_ms"] >= 0 for row in stages)
    build = stages[-1]
    assert build["status"] == "failed"
    assert "Could not locate the Next.js project root" in build["summary"]
    assert build["log_path"].startswith("storage/observability/site_roll_logs/")
    log = (tmp_path / build["log_path"]).read_text(encoding="utf-8")
    assert "super-secret-value" not in log
    assert "token=[REDACTED]" in log
    assert "super-secret-value" not in json.dumps(record)


def test_wrapped_sensing_timeline_uses_immutable_manifests(tmp_path):
    manifests = tmp_path / "storage/observability/manifests"
    logs = tmp_path / "storage/observability/logs"
    manifests.mkdir(parents=True)
    logs.mkdir(parents=True)
    log = logs / "s01.log"
    log.write_text("ok\n", encoding="utf-8")
    (manifests / "s01.json").write_text(
        json.dumps(
            {
                "lane": "sensing",
                "stage": "s01",
                "status": "success",
                "started_at": "2026-08-25T02:00:00Z",
                "ended_at": "2026-08-25T02:00:02.250Z",
                "command": ["make", "s01", "DIGEST_AT=20260825T02"],
                "log_path": str(log.relative_to(tmp_path)),
            }
        ),
        encoding="utf-8",
    )
    rows = wrapped_stage_timeline(tmp_path, lane="sensing", digest_at="20260825T02")
    assert len(rows) == 1
    assert rows[0]["stage"] == "s01"
    assert rows[0]["status"] == "success"
    assert rows[0]["duration_ms"] == 2250
    assert rows[0]["log_path"] == "storage/observability/logs/s01.log"


class RefreshFailureRunner:
    def __call__(self, command, *, cwd, env=None):
        if command == ["vercel", "--version"]:
            return Result(command, 0, "Vercel CLI 58.9.5\n", "")
        if command[:2] == ["bin/run_minimal_loop_once.sh", "--lane"]:
            return Result(command, 0, "sensing ok", "")

        log = cwd / "storage/observability/site_roll_logs/pull.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[stderr]\nWarning: The vercel.json file should be inside of the provided root directory.\n",
            encoding="utf-8",
        )
        payload = {
            "status": "failed",
            "failed_stage": "build",
            "error": "build failed (exit 1)",
            "roll": {
                "stages": [
                    {"stage": "pull", "status": "ok", "duration_ms": 220, "log_path": "storage/observability/site_roll_logs/pull.log", "summary": None},
                    {
                        "stage": "build",
                        "status": "failed",
                        "duration_ms": 1430,
                        "log_path": "storage/observability/site_roll_logs/build.log",
                        "summary": "Error: Next build failed for a useful reason",
                    },
                ]
            },
        }
        return Result(command, 1, json.dumps(payload), "")


def test_refresh_promotes_publication_stage_summary_log_and_warnings(tmp_path):
    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T02",
        runner=RefreshFailureRunner(),
        python_executable="python-test",
    )
    assert code == 1
    assert report["provider_stages"][0]["status"] == "ok"
    assert report["failed_lane"] == "publication"
    assert report["failed_stage"] == "build"
    assert report["error"] == "Error: Next build failed for a useful reason"
    assert report["diagnostic_log"] == "storage/observability/site_roll_logs/build.log"
    assert [row["stage"] for row in report["publication_stages"]] == ["pull", "build"]
    assert "vercel.json file should be inside" in report["publication_stages"][0]["warnings"][0]
