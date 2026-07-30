from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from apps.news_acquire.src.news_acquire.s3_store import S3Layout, S3SensingStore


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.puts: list[dict] = []

    def put_object(self, **kwargs):
        key = (kwargs["Bucket"], kwargs["Key"])
        if kwargs.get("IfNoneMatch") == "*" and key in self.objects:
            raise RuntimeError("PreconditionFailed")
        body = kwargs["Body"]
        self.objects[key] = body if isinstance(body, bytes) else body.read()
        self.puts.append(kwargs)
        return {}

    def list_objects_v2(self, **kwargs):
        prefix = kwargs["Prefix"]
        contents = [
            {"Key": key}
            for bucket, key in sorted(self.objects)
            if bucket == kwargs["Bucket"] and key.startswith(prefix)
        ]
        return {"Contents": contents, "IsTruncated": False}

    def get_object(self, **kwargs):
        return {"Body": io.BytesIO(self.objects[(kwargs["Bucket"], kwargs["Key"])])}


def bundle_fixture(tmp_path: Path) -> Path:
    bundle = tmp_path / "sensing:20260729T00:attempt:1:test"
    (bundle / "candidates").mkdir(parents=True)
    manifest = {
        "schema_version": "sensing_run_bundle.v1",
        "run_id": bundle.name,
        "digest_at": "20260729T00",
        "status": "success",
        "source_commit": "commit123",
        "image_digest": "sha256:image123",
    }
    (bundle / "candidates" / "news_recent_refs.jsonl").write_text("{}\n")
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    (bundle / "FINALIZED").write_text("success\n")
    return bundle


def test_producer_writes_only_one_immutable_run_prefix_and_marker_last(tmp_path: Path) -> None:
    client = FakeS3()
    store = S3SensingStore(client, "bucket", S3Layout("tenant/sensing"), "producer")
    bundle = bundle_fixture(tmp_path)

    keys = store.upload_run_bundle(bundle)

    assert all(key.startswith(f"tenant/sensing/runs/{bundle.name}/") for key in keys)
    assert keys[-1].endswith("/FINALIZED")
    assert all(call.get("IfNoneMatch") == "*" for call in client.puts)
    assert store.upload_run_bundle(bundle) == keys
    (bundle / "candidates" / "news_recent_refs.jsonl").write_text('{"changed":true}\n')
    with pytest.raises(RuntimeError, match="PreconditionFailed"):
        store.upload_run_bundle(bundle)
    with pytest.raises(PermissionError):
        store.upload_compaction(tmp_path / "generation", {"generation": "generation"})


def test_compactor_can_discover_and_download_but_producer_cannot(tmp_path: Path) -> None:
    client = FakeS3()
    producer = S3SensingStore(client, "bucket", S3Layout(), "producer")
    bundle = bundle_fixture(tmp_path / "source")
    producer.upload_run_bundle(bundle)
    compactor = S3SensingStore(client, "bucket", S3Layout(), "compactor")

    assert compactor.list_finalized_runs() == [bundle.name]
    downloaded = compactor.download_run_bundle(bundle.name, tmp_path / "downloads")
    assert json.loads((downloaded / "manifest.json").read_text())["image_digest"] == "sha256:image123"
    with pytest.raises(PermissionError):
        producer.list_finalized_runs()


def test_only_compactor_writes_generation_and_latest_pointer_last(tmp_path: Path) -> None:
    client = FakeS3()
    store = S3SensingStore(client, "bucket", S3Layout(), "compactor")
    generation = tmp_path / "generation123"
    generation.mkdir()
    (generation / "master_ref.csv").write_text("index_id\n")
    pointer = {"generation": generation.name, "latest_run_id": "run"}

    keys = store.upload_compaction(generation, pointer)

    assert keys[0] == "media-monitor/sensing/compacted/generation123/master_ref.csv"
    assert keys[-1] == "media-monitor/sensing/latest/current.json"
    assert client.puts[0]["IfNoneMatch"] == "*"
    assert "IfNoneMatch" not in client.puts[-1]
    uploaded_pointer = json.loads(client.objects[("bucket", keys[-1])])
    assert uploaded_pointer["generation_path"] == "media-monitor/sensing/compacted/generation123"


@pytest.mark.parametrize("value", ["", "../escape", "run/id", "run\\id"])
def test_layout_rejects_unsafe_run_ids(value: str) -> None:
    with pytest.raises(ValueError):
        S3Layout().run_prefix(value)
