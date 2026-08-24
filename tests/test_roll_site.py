import json
import os
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from roll_site import Result, roll


def snapshot(root, site="argentina-general", digest="20260721T18"):
    path = root / "apps/news_site/public/data/site_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_name": "site_snapshot.v3",
                "site": {"site_id": site},
                "digest_at": digest,
                "snapshot_id": "a" * 64,
                "metrics": {
                    "item_count": 11,
                    "section_count": 1,
                    "published_article_count": 2,
                    "curated_signal_count": 6,
                },
            }
        )
    )
    return path


def healthy_publication(**overrides):
    payload = {
        "schema_name": "publication_health.v1",
        "freshness_status": "FRESH",
        "is_current": True,
        "within_target": True,
        "age_minutes": 20,
    }
    payload.update(overrides)
    return payload


def default_health():
    return {
        "status": "ok",
        "site_id": "argentina-general",
        "snapshot_id": "a" * 64,
        "digest_at": "20260721T18",
        "item_count": 11,
        "section_count": 1,
        "published_article_count": 2,
        "curated_signal_count": 6,
        "publication_health": healthy_publication(),
    }


class Fake:
    def __init__(self, root, deploy="noise\nhttps://roll-abc.vercel.app\n", health=None, fail=None):
        self.root = root
        self.deploy = deploy
        self.health = default_health() if health is None else health
        self.fail = fail
        self.calls = []
        self.health_calls = 0

    def __call__(self, command, *, cwd, env=None):
        self.calls.append((command, env))
        if self.fail and self.fail == command[0:2]:
            return Result(command, 1, "", "bad")
        if command[:2] == ["vercel", "build"]:
            out = self.root / ".vercel/output"
            out.mkdir(parents=True)
            (out / "config.json").write_text("{}")
            os.utime(out, (time.time() + 1, time.time() + 1))
        if command[:2] == ["vercel", "deploy"]:
            return Result(command, 0, self.deploy, "progress")
        if command[:2] == ["vercel", "curl"]:
            self.health_calls += 1
            value = self.health[self.health_calls - 1] if isinstance(self.health, list) else self.health
            return Result(command, 0, value if isinstance(value, str) else json.dumps(value), "")
        return Result(command, 0, "", "")


def latest(root):
    return json.loads(next((root / "storage/observability").glob("site_roll_latest_*.json")).read_text())


def test_successful_preview_roll_rebuilds_publication_index_first(tmp_path):
    snapshot(tmp_path)
    fake = Fake(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, fake, lambda _: None)
    assert code == 0 and record["status"] == "ok"
    commands = [call[0] for call in fake.calls]
    assert commands[0][:2] == ["make", "build-published-article-indexes"]
    assert any("scripts/build_editorial_selection.py" in command for command in commands)
    assert ["vercel", "pull", "--yes", "--environment=preview"] in commands
    assert record["expected"]["published_article_count"] == 2
    assert record["expected"]["curated_signal_count"] == 6
    assert latest(tmp_path)["snapshot_id"] == "a" * 64


def test_production_command_construction_and_freshness_record(tmp_path):
    snapshot(tmp_path)
    fake = Fake(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "production", tmp_path, fake, lambda _: None)
    assert code == 0
    commands = [call[0] for call in fake.calls]
    assert ["vercel", "build", "--prod"] in commands
    assert ["vercel", "deploy", "--prebuilt", "--prod"] in commands
    assert record["observed"]["freshness_status"] == "FRESH"
    assert record["observed"]["within_target"] is True
    assert record["observed"]["published_article_count"] == 2
    assert record["observed"]["curated_signal_count"] == 6


def test_ci_token_is_forwarded_without_entering_roll_record(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "ci-secret-token")
    monkeypatch.setenv("CI_MARKER", "preserved")
    snapshot(tmp_path)
    fake = Fake(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "production", tmp_path, fake, lambda _: None)
    assert code == 0
    vercel_calls = [command for command, _ in fake.calls if command[0] == "vercel"]
    assert vercel_calls
    assert all(command[-2:] == ["--token", "ci-secret-token"] for command in vercel_calls)
    build_env = next(env for command, env in fake.calls if command[:2] == ["vercel", "build"])
    assert build_env["CI_MARKER"] == "preserved"
    assert build_env["SITE_ID"] == "argentina-general"
    assert build_env["DIGEST_AT"] == "20260721T18"
    assert "ci-secret-token" not in json.dumps(record)
    assert "ci-secret-token" not in json.dumps(latest(tmp_path))


def test_production_target_miss_fails_health_gate(tmp_path):
    snapshot(tmp_path)
    health = default_health()
    health["publication_health"] = healthy_publication(within_target=False, age_minutes=150)
    record, code = roll("argentina-general", "20260721T18", "production", tmp_path, Fake(tmp_path, health=health), lambda _: None)
    assert code == 1
    assert record["failed_stage"] == "health"
    assert "missed freshness target" in record["error"]


def test_production_stale_health_fails(tmp_path):
    snapshot(tmp_path)
    health = default_health()
    health["publication_health"] = healthy_publication(freshness_status="STALE", is_current=False, within_target=False, age_minutes=500)
    record, code = roll("argentina-general", "20260721T18", "production", tmp_path, Fake(tmp_path, health=health), lambda _: None)
    assert code == 1 and record["failed_stage"] == "health"


def test_publication_count_identity_mismatch_fails(tmp_path):
    snapshot(tmp_path)
    health = default_health() | {"published_article_count": 1}
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, health=health), lambda _: None)
    assert code == 1 and record["failed_stage"] == "health"


def test_curated_count_identity_mismatch_fails(tmp_path):
    snapshot(tmp_path)
    health = default_health() | {"curated_signal_count": 5}
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, health=health), lambda _: None)
    assert code == 1 and record["failed_stage"] == "health"


def test_invalid_target_never_defaults_production(tmp_path):
    snapshot(tmp_path)
    try:
        roll("argentina-general", "20260721T18", "", tmp_path, Fake(tmp_path))
    except ValueError:
        pass
    else:
        assert False


def test_snapshot_mismatch_fails_before_vercel(tmp_path):
    snapshot(tmp_path, digest="wrong")
    fake = Fake(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, fake)
    assert code and record["failed_stage"] == "identity"
    assert not any(call[0][0] == "vercel" for call in fake.calls)


def test_publication_index_failure_stops_before_snapshot_or_vercel(tmp_path):
    snapshot(tmp_path)
    fake = Fake(tmp_path, fail=["make", "build-published-article-indexes"])
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, fake)
    assert code == 1 and record["failed_stage"] == "publication-index"
    assert not any(call[0][0] == "vercel" for call in fake.calls)


def test_build_failure(tmp_path):
    snapshot(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, fail=["vercel", "build"]))
    assert code and record["failed_stage"] == "build"


def test_missing_output(tmp_path):
    snapshot(tmp_path)

    def runner(command, **kwargs):
        return Result(command, 0, "https://x.vercel.app" if command[:2] == ["vercel", "deploy"] else "", "")

    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, runner)
    assert code and record["failed_stage"] == "build"


def test_url_extraction_and_missing_host(tmp_path):
    snapshot(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, deploy="log https://x.vercel.app end"))
    assert code == 0 and record["deployment_host"] == "x.vercel.app"

    snapshot(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, deploy="no url"))
    assert code and record["failed_stage"] == "deploy"


def test_malformed_health_and_identity_mismatches(tmp_path):
    bad_values = [
        "not json",
        default_health() | {"snapshot_id": "bad"},
        default_health() | {"digest_at": "bad"},
        default_health() | {"item_count": 1},
    ]
    for bad in bad_values:
        snapshot(tmp_path)
        record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, health=bad), lambda _: None)
        assert code and record["failed_stage"] == "health"


def test_health_retries_and_failure_record_is_safe(tmp_path):
    snapshot(tmp_path)
    fake = Fake(tmp_path, health=["no", default_health()])
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, fake, lambda _: None)
    assert code == 0 and fake.health_calls == 2

    snapshot(tmp_path)
    record, code = roll("argentina-general", "20260721T18", "preview", tmp_path, Fake(tmp_path, deploy="token=secret"), lambda _: None)
    assert code == 1
    assert "secret" not in json.dumps(latest(tmp_path))


def test_no_ingestion_or_editorial_generation_commands(tmp_path):
    snapshot(tmp_path)
    fake = Fake(tmp_path)
    roll("argentina-general", "20260721T18", "preview", tmp_path, fake, lambda _: None)
    forbidden = ("s01", "ingestion", "export-pr3a", "draft-article", "s04", "promptflow")
    assert all(
        not any(word in " ".join(call[0]).lower() for word in forbidden)
        for call in fake.calls
    )
