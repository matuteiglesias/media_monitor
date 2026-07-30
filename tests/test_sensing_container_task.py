from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_sensing_task import run_denial_probe


def test_sensing_dockerfile_is_narrow_non_root_and_secret_free() -> None:
    dockerfile = (ROOT / "Dockerfile.sensing").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "USER sensing" in dockerfile
    assert 'ENTRYPOINT ["python", "scripts/run_sensing_task.py"]' in dockerfile
    assert "COPY --chown=sensing:sensing apps/news_acquire" in dockerfile
    assert "apps/news_editorial" not in dockerfile
    assert "apps/news_enrich" not in dockerfile
    assert "apps/news_site" not in dockerfile
    assert ".env" not in dockerfile
    assert ".env" in dockerignore
    assert "data" in dockerignore
    assert "storage" in dockerignore


def test_sensing_requirements_are_exactly_pinned() -> None:
    requirements = (ROOT / "requirements-sensing.txt").read_text(encoding="utf-8").splitlines()

    assert requirements
    assert all("==" in line for line in requirements if line.strip())
    assert any(line.startswith("boto3==") for line in requirements)


def test_task_configuration_failure_is_structured_and_nonzero() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_sensing_task.py"],
        cwd=ROOT,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    event = json.loads(result.stdout)
    assert event["event"] == "task_error"
    assert event["lane"] == "sensing"
    assert event["error_type"] == "ValueError"
    assert result.stderr == ""


def test_iam_denial_probe_requires_access_denied(capsys) -> None:
    class Denied(Exception):
        response = {"Error": {"Code": "AccessDenied"}}

    client = types.SimpleNamespace(
        put_object=lambda **_kwargs: (_ for _ in ()).throw(Denied("denied"))
    )
    store = types.SimpleNamespace(client=client, bucket="bucket")

    run_denial_probe(store, "media-monitor/sensing", "run-id")

    event = json.loads(capsys.readouterr().out)
    assert event["event"] == "iam_denial_confirmed"
    assert event["run_id"] == "run-id"
