import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from error_surface import summarize_failure
from media_refresh import refresh
from roll_site import Result


class FakeRunner:
    def __init__(self, sensing_code=0, publish_code=0):
        self.calls = []
        self.sensing_code = sensing_code
        self.publish_code = publish_code

    def __call__(self, command, *, cwd, env=None):
        self.calls.append((command, env or {}))
        if command[:2] == ["bin/run_minimal_loop_once.sh", "--lane"]:
            return Result(command, self.sensing_code, "sensing ok" if not self.sensing_code else "", "sensing failed" if self.sensing_code else "")
        if "scripts/media_ops.py" in command:
            payload = (
                '{"status":"ok","snapshot_id":"abc","deployment_host":"preview.vercel.app","item_count":12,"section_count":4}'
                if not self.publish_code
                else '{"status":"failed","failed_stage":"editorial-selection","error":"selection failed"}'
            )
            return Result(command, self.publish_code, payload, "")
        raise AssertionError(command)


def test_refresh_runs_live_sensing_then_publishes_exact_same_digest(tmp_path):
    runner = FakeRunner()
    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=runner,
        python_executable="python-test",
    )
    assert code == 0 and report["status"] == "ok"
    assert report["digest_at"] == "20260825T01"
    sensing_command, sensing_env = runner.calls[0]
    assert sensing_command == ["bin/run_minimal_loop_once.sh", "--lane", "sensing"]
    assert sensing_env["DIGEST_AT"] == "20260825T01"
    assert sensing_env["DRY_RUN"] == "0"
    assert sensing_env["ACQUIRE_NETWORK"] == "1"
    assert sensing_env["WRITE_ARTIFACTS"] == "1"
    assert sensing_env["ENQUEUE_SCRAPE"] == "0"
    assert sensing_env["TRIGGER_TYPE"] == "manual"
    publish_command, _ = runner.calls[1]
    assert publish_command[:4] == ["python-test", "scripts/media_ops.py", "--repo-root", str(tmp_path.resolve())]
    assert publish_command[publish_command.index("--digest-at") + 1] == "20260825T01"
    assert publish_command[publish_command.index("--target") + 1] == "preview"


def test_refresh_never_publishes_if_live_sensing_fails(tmp_path):
    runner = FakeRunner(sensing_code=9)
    report, code = refresh(
        site_id="argentina-general",
        target="production",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=runner,
    )
    assert code == 1
    assert report["failed_lane"] == "sensing"
    assert report["failed_stage"] == "sensing"
    assert report["error"] == "sensing failed"
    assert len(runner.calls) == 1


def test_refresh_promotes_failed_stage_root_cause_and_log(tmp_path):
    log = tmp_path / "storage/observability/logs/export-failure.log"
    log.parent.mkdir(parents=True)
    log.write_text(
        "[stdout]\n"
        "[pr3a-export] ERROR export failed: ValueError: news_digest_group.v1 row 0 invalid: "
        "['recent_4h_window is not one of the allowed window types']\n"
        "[stderr]\nmake: *** [Makefile:155: export-pr3a] Error 1\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "storage/observability/manifests/export-failure.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "lane": "sensing",
                "stage": "export_pr3a",
                "status": "failed",
                "command": ["make", "export-pr3a", "DIGEST_AT=20260825T01"],
                "log_path": "storage/observability/logs/export-failure.log",
            }
        ),
        encoding="utf-8",
    )

    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=FakeRunner(sensing_code=2),
    )
    assert code == 1
    assert report["failed_lane"] == "sensing"
    assert report["failed_stage"] == "export_pr3a"
    assert "recent_4h_window" in report["error"]
    assert "make: ***" not in report["error"]
    assert report["diagnostic_log"] == "storage/observability/logs/export-failure.log"


def test_failure_summary_redacts_secrets_and_prefers_semantic_error():
    summary = summarize_failure(
        "[worker] ERROR: upstream rejected token=very-secret-value\n",
        "make: *** [target] Error 1\n",
    )
    assert "very-secret-value" not in summary
    assert "token=[REDACTED]" in summary
    assert "make: ***" not in summary


def test_refresh_reports_downstream_publish_failure_without_rewriting_it(tmp_path):
    runner = FakeRunner(publish_code=1)
    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=runner,
    )
    assert code == 1
    assert report["failed_lane"] == "publication"
    assert report["failed_stage"] == "editorial-selection"
    assert report["error"] == "selection failed"
