from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

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
    assert report["failed_stage"] == "sensing"
    assert len(runner.calls) == 1


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
    assert report["failed_stage"] == "editorial-selection"
    assert report["error"] == "selection failed"
