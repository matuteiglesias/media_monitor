import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from error_surface import summarize_failure
from media_refresh import refresh
from roll_site import Result


class FakeRunner:
    def __init__(self, sensing_code=0, publish_code=0, vercel_version="58.9.5"):
        self.calls = []
        self.sensing_code = sensing_code
        self.publish_code = publish_code
        self.vercel_version = vercel_version

    def __call__(self, command, *, cwd, env=None):
        self.calls.append((command, env or {}))
        if command == ["vercel", "--version"]:
            return Result(command, 0, f"Vercel CLI {self.vercel_version}\n", "")
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


def test_refresh_preflights_provider_then_runs_live_sensing_and_exact_digest(tmp_path):
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
    assert runner.calls[0][0] == ["vercel", "--version"]
    assert report["provider"]["version"] == "58.9.5"
    assert report["provider_stages"][0]["status"] == "ok"

    sensing_command, sensing_env = runner.calls[1]
    assert sensing_command == ["bin/run_minimal_loop_once.sh", "--lane", "sensing"]
    assert sensing_env["DIGEST_AT"] == "20260825T01"
    assert sensing_env["DRY_RUN"] == "0"
    assert sensing_env["ACQUIRE_NETWORK"] == "1"
    assert sensing_env["WRITE_ARTIFACTS"] == "1"
    assert sensing_env["ENQUEUE_SCRAPE"] == "0"
    assert sensing_env["TRIGGER_TYPE"] == "manual"
    publish_command, _ = runner.calls[2]
    assert publish_command[:4] == ["python-test", "scripts/media_ops.py", "--repo-root", str(tmp_path.resolve())]
    assert publish_command[publish_command.index("--digest-at") + 1] == "20260825T01"
    assert publish_command[publish_command.index("--target") + 1] == "preview"


def test_refresh_refuses_obsolete_vercel_before_sensing(tmp_path):
    runner = FakeRunner(vercel_version="46.0.5")
    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=runner,
    )
    assert code == 1
    assert report["failed_lane"] == "provider"
    assert report["failed_stage"] == "vercel-cli"
    assert "46.0.5" in report["error"]
    assert "47.2.2" in report["error"]
    assert "vercel@latest" in report["error"]
    assert len(runner.calls) == 1


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
    assert len(runner.calls) == 2


def test_refresh_promotes_failed_stage_root_cause_and_log(tmp_path):
    class FailingSensingRunner:
        def __call__(self, command, *, cwd, env=None):
            if command == ["vercel", "--version"]:
                return Result(command, 0, "Vercel CLI 58.9.5\n", "")
            log = cwd / "storage/observability/logs/export-failure.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(
                "[stdout]\n"
                "[pr3a-export] ERROR export failed: ValueError: news_digest_group.v1 row 0 invalid: "
                "['recent_4h_window is not one of the allowed window types']\n"
                "[stderr]\nmake: *** [Makefile:155: export-pr3a] Error 1\n",
                encoding="utf-8",
            )
            manifest = cwd / "storage/observability/manifests/export-failure.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            manifest.write_text(
                json.dumps(
                    {
                        "lane": "sensing",
                        "stage": "export_pr3a",
                        "status": "failed",
                        "started_at": now,
                        "ended_at": now,
                        "command": ["make", "export-pr3a", "DIGEST_AT=20260825T01"],
                        "log_path": "storage/observability/logs/export-failure.log",
                    }
                ),
                encoding="utf-8",
            )
            return Result(command, 2, "", "sensing failed")

    report, code = refresh(
        site_id="argentina-general",
        target="preview",
        repo_root=tmp_path,
        digest_at="20260825T01",
        runner=FailingSensingRunner(),
    )
    assert code == 1
    assert report["failed_lane"] == "sensing"
    assert report["failed_stage"] == "export_pr3a"
    assert "recent_4h_window" in report["error"]
    assert "make: ***" not in report["error"]
    assert report["diagnostic_log"] == "storage/observability/logs/export-failure.log"
    assert report["sensing_stages"][0]["stage"] == "export_pr3a"


def test_failure_summary_redacts_secrets_and_prefers_semantic_error():
    summary = summarize_failure(
        "[worker] ERROR: upstream rejected token=very-secret-value\n",
        "make: *** [target] Error 1\n",
    )
    assert "very-secret-value" not in summary
    assert "token=[REDACTED]" in summary
    assert "make: ***" not in summary


def test_failure_summary_prefers_actionable_provider_error_over_final_abort():
    summary = summarize_failure(
        "",
        "\n".join(
            [
                "Vercel CLI 46.0.5",
                'Error: Your Vercel CLI version is outdated. This endpoint requires version 47.2.2 or later. Please upgrade by running `npm i -g vercel@latest`.',
                "Error: AbortError: The user aborted a request.",
                "Error: Upload aborted",
            ]
        ),
    )
    assert "version is outdated" in summary
    assert "47.2.2" in summary
    assert "Upload aborted" not in summary


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
