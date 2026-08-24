import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from media_ops import Result, doctor, publish, resolve_digest, status


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def ready_root(root: Path, digest: str = "20260817T03") -> None:
    write_json(
        root / "sites/argentina-general.json",
        {
            "site_id": "argentina-general",
            "name": "Actualidad Argentina",
            "tagline": "Noticias recientes de Argentina",
            "locale": "es-AR",
            "selection": {
                "topics": ["All Topics"],
                "max_age_hours": 3,
                "minimum_items": 5,
                "max_items": 40,
            },
            "presentation": {"latest_count": 12, "show_sources": True},
        },
    )
    write_json(root / "storage/indexes/pr3a_exports_latest.json", {"digest_at": digest})
    write_json(root / ".vercel/project.json", {"projectId": "prj_123", "orgId": "team_123"})
    for relative in (
        "scripts/build_news_access_indexes.py",
        "scripts/build_site_snapshot.py",
        "scripts/validate_site_snapshot.py",
        "scripts/roll_site.py",
        "apps/news_site/package.json",
        "apps/news_site/package-lock.json",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def snapshot_payload(digest: str = "20260817T03", snapshot_id: str = "a" * 64) -> dict:
    return {
        "site": {"site_id": "argentina-general"},
        "digest_at": digest,
        "snapshot_id": snapshot_id,
        "generated_at": "2026-08-17T03:30:00Z",
        "metrics": {"item_count": 12, "section_count": 2},
    }


def roll_payload(digest: str = "20260817T03", snapshot_id: str = "a" * 64, status_value: str = "ok") -> dict:
    return {
        "schema_name": "site_roll.v1",
        "status": status_value,
        "site_id": "argentina-general",
        "target": "production",
        "digest_at": digest,
        "snapshot_id": snapshot_id,
        "expected": {"item_count": 12, "section_count": 2},
        "deployment_host": "media-prod.vercel.app",
        "completed_at": "2026-08-17T03:35:00Z",
        "failed_stage": None,
        "error": None,
    }


class FakeRunner:
    def __init__(self, health=None, diagnose=None):
        self.calls = []
        self.health = health
        self.diagnose = diagnose

    def __call__(self, command, *, cwd, env=None):
        self.calls.append(command)
        if command[:2] == ["vercel", "curl"]:
            payload = self.health if self.health is not None else {
                "status": "ok",
                "site_id": "argentina-general",
                "snapshot_id": "a" * 64,
                "digest_at": "20260817T03",
                "item_count": 12,
                "section_count": 2,
            }
            return Result(command, 0, json.dumps(payload), "")
        if command[:2] == ["vercel", "whoami"]:
            return Result(command, 0, "matuteiglesias\n", "")
        if "--diagnose" in command:
            payload = self.diagnose if self.diagnose is not None else {
                "inputs": [
                    {"export_name": "news_ref.v1", "exists": True, "rows": 8, "digest_at": "20260817T03"},
                    {"export_name": "news_digest_group.v1", "exists": True, "rows": 2, "digest_at": "20260817T03"},
                ]
            }
            return Result(command, 0, json.dumps(payload), "")
        return Result(command, 0, "", "")


def all_tools(_name: str) -> str:
    return "/usr/bin/fake"


def test_resolve_digest_prefers_explicit_and_otherwise_leases_latest(tmp_path):
    ready_root(tmp_path)
    assert resolve_digest(tmp_path) == "20260817T03"
    assert resolve_digest(tmp_path, "20260816T22") == "20260816T22"


def test_status_matches_record_and_remote_identity(tmp_path):
    ready_root(tmp_path)
    write_json(tmp_path / "apps/news_site/public/data/site_snapshot.json", snapshot_payload())
    write_json(tmp_path / "storage/runs/site_roll_argentina-general_20260817T03_x.json", roll_payload())
    report, code = status(
        "argentina-general",
        "production",
        tmp_path,
        runner=FakeRunner(),
        which=all_tools,
        now=datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc),
    )
    assert code == 0
    assert report["status"] == "ok"
    assert report["remote"]["matches_roll_record"] is True
    assert report["remote"]["matches_local_snapshot"] is True


def test_status_treats_local_drift_as_warning_but_remote_record_mismatch_as_failure(tmp_path):
    ready_root(tmp_path)
    write_json(tmp_path / "apps/news_site/public/data/site_snapshot.json", snapshot_payload(snapshot_id="b" * 64))
    write_json(tmp_path / "storage/runs/site_roll_argentina-general_20260817T03_x.json", roll_payload())
    report, code = status(
        "argentina-general",
        "production",
        tmp_path,
        runner=FakeRunner(),
        which=all_tools,
        now=datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc),
    )
    assert code == 0 and report["status"] == "warn"
    assert any("local snapshot differs" in item for item in report["warnings"])

    bad_health = {
        "status": "ok",
        "site_id": "argentina-general",
        "snapshot_id": "c" * 64,
        "digest_at": "20260817T03",
        "item_count": 12,
        "section_count": 2,
    }
    report, code = status(
        "argentina-general",
        "production",
        tmp_path,
        runner=FakeRunner(health=bad_health),
        which=all_tools,
        now=datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc),
    )
    assert code == 1 and report["status"] == "fail"
    assert any("does not match" in item for item in report["failures"])


def test_doctor_is_read_only_and_reports_publish_readiness(tmp_path):
    ready_root(tmp_path)
    runner = FakeRunner()
    report, code = doctor(
        "argentina-general",
        "preview",
        tmp_path,
        runner=runner,
        which=all_tools,
        python_executable=sys.executable,
    )
    assert code == 0 and report["ready"] is True
    assert report["digest_at"] == "20260817T03"
    assert any(row["name"] == "publish-inputs" and row["status"] == "pass" for row in report["checks"])
    assert not any(call and call[0] == "make" for call in runner.calls)


def test_doctor_blocks_missing_vercel_link_and_empty_inputs(tmp_path):
    ready_root(tmp_path)
    (tmp_path / ".vercel/project.json").unlink()
    runner = FakeRunner(
        diagnose={
            "inputs": [
                {"export_name": "news_ref.v1", "exists": True, "rows": 0, "digest_at": "20260817T03"},
                {"export_name": "news_digest_group.v1", "exists": True, "rows": 2, "digest_at": "20260817T03"},
            ]
        }
    )
    report, code = doctor("argentina-general", "preview", tmp_path, runner=runner, which=all_tools)
    assert code == 1 and report["ready"] is False
    failures = {row["name"] for row in report["checks"] if row["status"] == "fail"}
    assert {"vercel-project-link", "publish-inputs"}.issubset(failures)


def test_publish_aborts_before_mutation_when_doctor_blocks(tmp_path):
    ready_root(tmp_path)
    runner = FakeRunner()

    def blocked_doctor(*args, **kwargs):
        return {"ready": False, "status": "fail", "checks": []}, 1

    def should_not_roll(*args, **kwargs):
        raise AssertionError("roll should not run")

    report, code = publish(
        "argentina-general",
        "preview",
        tmp_path,
        runner=runner,
        doctor_fn=blocked_doctor,
        roll_fn=should_not_roll,
    )
    assert code == 1 and report["failed_stage"] == "doctor"
    assert not any(call and call[0] == "make" for call in runner.calls)


def test_publish_leases_one_digest_refreshes_indexes_then_delegates_to_roll(tmp_path):
    ready_root(tmp_path)
    runner = FakeRunner()
    captured = {}

    def ready_doctor(site_id, target, root, **kwargs):
        captured["doctor_digest"] = kwargs["digest_at"]
        return {"ready": True, "status": "ok", "checks": []}, 0

    def fake_roll(site_id, digest_at, target, root, **kwargs):
        captured["roll_digest"] = digest_at
        captured["roll_target"] = target
        return {
            "status": "ok",
            "site_id": site_id,
            "target": target,
            "digest_at": digest_at,
            "snapshot_id": "a" * 64,
            "snapshot_sha256": "d" * 64,
            "expected": {"item_count": 12, "section_count": 2},
            "deployment_host": "preview.vercel.app",
            "git_sha": "deadbeef",
        }, 0

    report, code = publish(
        "argentina-general",
        "preview",
        tmp_path,
        runner=runner,
        doctor_fn=ready_doctor,
        roll_fn=fake_roll,
    )
    assert code == 0 and report["status"] == "ok"
    assert captured == {"doctor_digest": "20260817T03", "roll_digest": "20260817T03", "roll_target": "preview"}
    make_calls = [call for call in runner.calls if call and call[0] == "make"]
    assert make_calls == [["make", "build-news-access-indexes", "DIGEST_AT=20260817T03", f"PYTHON={sys.executable}"]]


def test_publish_default_cli_target_is_preview():
    from media_ops import build_parser

    args = build_parser().parse_args(["publish"])
    assert args.target == "preview"
