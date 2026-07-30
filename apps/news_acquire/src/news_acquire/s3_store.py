"""Least-authority S3 storage seams for sensing producers and compactors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal


Actor = Literal["producer", "compactor"]


def _safe_component(value: str, name: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"invalid {name}: {value!r}")
    return value


def _relative_key(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if not relative or ".." in PurePosixPath(relative).parts:
        raise ValueError(f"path escapes root: {path}")
    return relative


@dataclass(frozen=True)
class S3Layout:
    prefix: str = "media-monitor/sensing"

    def __post_init__(self) -> None:
        normalized = self.prefix.strip("/")
        if not normalized or ".." in PurePosixPath(normalized).parts:
            raise ValueError("S3 prefix must be a safe non-empty key prefix")
        object.__setattr__(self, "prefix", normalized)

    def run_prefix(self, run_id: str) -> str:
        return f"{self.prefix}/runs/{_safe_component(run_id, 'run_id')}"

    def generation_prefix(self, generation: str) -> str:
        return f"{self.prefix}/compacted/{_safe_component(generation, 'generation')}"

    @property
    def runs_prefix(self) -> str:
        return f"{self.prefix}/runs/"

    @property
    def current_key(self) -> str:
        return f"{self.prefix}/latest/current.json"


class S3SensingStore:
    def __init__(self, client, bucket: str, layout: S3Layout, actor: Actor) -> None:
        if actor not in {"producer", "compactor"}:
            raise ValueError(f"invalid actor: {actor}")
        self.client = client
        self.bucket = bucket
        self.layout = layout
        self.actor = actor

    def _require(self, actor: Actor) -> None:
        if self.actor != actor:
            raise PermissionError(f"{self.actor} cannot perform {actor}-owned storage operation")

    def _put_immutable(self, key: str, body: bytes, content_type: str | None = None) -> None:
        kwargs = {"Bucket": self.bucket, "Key": key, "Body": body, "IfNoneMatch": "*"}
        if content_type:
            kwargs["ContentType"] = content_type
        try:
            self.client.put_object(**kwargs)
        except Exception:
            # Retry is idempotent only when the already-present immutable bytes match.
            existing = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
            if existing != body:
                raise

    def upload_run_bundle(self, bundle: Path) -> list[str]:
        """Producer upload: immutable objects beneath exactly one run prefix."""
        self._require("producer")
        if not (bundle / "FINALIZED").is_file() or not (bundle / "manifest.json").is_file():
            raise ValueError(f"not a finalized run bundle: {bundle}")
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        run_id = _safe_component(str(manifest.get("run_id") or ""), "run_id")
        if bundle.name != run_id:
            raise ValueError("bundle directory does not match manifest run_id")
        prefix = self.layout.run_prefix(run_id)
        files = sorted(path for path in bundle.rglob("*") if path.is_file())
        # Completion marker is always uploaded last; no append or shared key exists.
        files.sort(key=lambda path: (path.name == "FINALIZED", _relative_key(path, bundle)))
        keys: list[str] = []
        for path in files:
            relative = _relative_key(path, bundle)
            key = f"{prefix}/{relative}"
            self._put_immutable(key, path.read_bytes())
            keys.append(key)
        return keys

    def list_finalized_runs(self) -> list[str]:
        self._require("compactor")
        run_ids: set[str] = set()
        token: str | None = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": self.layout.runs_prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self.client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                key = str(item.get("Key") or "")
                if key.endswith("/FINALIZED"):
                    remainder = key[len(self.layout.runs_prefix) :]
                    run_id, separator, leaf = remainder.partition("/")
                    if separator and leaf == "FINALIZED":
                        run_ids.add(_safe_component(run_id, "run_id"))
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return sorted(run_ids)

    def download_run_bundle(self, run_id: str, destination: Path) -> Path:
        self._require("compactor")
        run_id = _safe_component(run_id, "run_id")
        target = destination / run_id
        if target.exists():
            raise FileExistsError(target)
        prefix = f"{self.layout.run_prefix(run_id)}/"
        token: str | None = None
        found = False
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self.client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                key = str(item["Key"])
                relative = key[len(prefix) :]
                if not relative or ".." in PurePosixPath(relative).parts:
                    raise ValueError(f"unsafe S3 run key: {key}")
                output = target / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                response_object = self.client.get_object(Bucket=self.bucket, Key=key)
                output.write_bytes(response_object["Body"].read())
                found = True
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        if not found:
            raise FileNotFoundError(f"no objects for run {run_id}")
        return target

    def upload_compaction(self, generation: Path, pointer: dict) -> list[str]:
        """Compactor upload: immutable generation first, mutable pointer last."""
        self._require("compactor")
        generation_id = _safe_component(str(pointer.get("generation") or ""), "generation")
        if generation.name != generation_id:
            raise ValueError("generation directory does not match pointer")
        prefix = self.layout.generation_prefix(generation_id)
        keys: list[str] = []
        for path in sorted(item for item in generation.rglob("*") if item.is_file()):
            key = f"{prefix}/{_relative_key(path, generation)}"
            self._put_immutable(key, path.read_bytes())
            keys.append(key)
        pointer_payload = dict(pointer)
        pointer_payload["generation_path"] = prefix
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.layout.current_key,
            Body=(json.dumps(pointer_payload, sort_keys=True, indent=2) + "\n").encode("utf-8"),
            ContentType="application/json",
        )
        keys.append(self.layout.current_key)
        return keys


def boto3_store(bucket: str, prefix: str, actor: Actor) -> S3SensingStore:
    import boto3

    return S3SensingStore(boto3.client("s3"), bucket, S3Layout(prefix), actor)
