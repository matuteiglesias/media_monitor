"""Deterministic single-writer compaction over immutable sensing bundles."""

from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from .run_bundle import sha256_file, utc_now_iso


ELIGIBLE_STATUSES = {"success", "partial_success", "empty_success"}
MASTER_COLUMNS = ["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"]


class InvalidBundle(ValueError):
    pass


@dataclass(frozen=True)
class ValidBundle:
    path: Path
    manifest: dict
    fingerprint: str

    @property
    def run_id(self) -> str:
        return str(self.manifest["run_id"])

    @property
    def digest_at(self) -> str:
        return str(self.manifest["digest_at"])

    @property
    def order_key(self) -> tuple[str, str, str]:
        return (self.digest_at, str(self.manifest.get("completed_at") or ""), self.run_id)


@dataclass(frozen=True)
class CompactionPlan:
    accepted: tuple[ValidBundle, ...]
    latest: ValidBundle | None
    rejected: tuple[dict, ...]
    generation: str


def discover_bundles(run_root: Path) -> list[Path]:
    runs = run_root / "runs"
    if not runs.exists():
        return []
    return sorted(path for path in runs.iterdir() if path.is_dir())


def validate_bundle(path: Path) -> ValidBundle:
    if not (path / "FINALIZED").is_file():
        raise InvalidBundle("missing FINALIZED marker")
    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidBundle(f"invalid manifest: {exc}") from exc
    if manifest.get("schema_version") != "sensing_run_bundle.v1":
        raise InvalidBundle("unsupported manifest schema")
    if manifest.get("run_id") != path.name:
        raise InvalidBundle("manifest run_id does not match directory")
    if manifest.get("status") not in ELIGIBLE_STATUSES:
        raise InvalidBundle(f"ineligible status {manifest.get('status')!r}")
    digest_at = manifest.get("digest_at")
    if not isinstance(digest_at, str) or len(digest_at) != 11:
        raise InvalidBundle("invalid digest_at")
    try:
        checksums = json.loads((path / "evidence" / "checksums.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidBundle(f"invalid checksums: {exc}") from exc
    if not isinstance(checksums, dict):
        raise InvalidBundle("checksums must be an object")
    for relative, expected in sorted(checksums.items()):
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise InvalidBundle(f"checksum path escapes bundle: {relative}")
        artifact = path / relative
        if not artifact.is_file() or sha256_file(artifact) != expected:
            raise InvalidBundle(f"checksum mismatch: {relative}")
    for candidate in ("news_recent_refs.jsonl", "news_recent_groups.jsonl"):
        if not (path / "candidates" / candidate).is_file():
            raise InvalidBundle(f"missing candidate: {candidate}")
    fingerprint_payload = {
        "run_id": manifest["run_id"],
        "digest_at": manifest["digest_at"],
        "completed_at": manifest.get("completed_at"),
        "status": manifest["status"],
        "checksums": checksums,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ValidBundle(path=path, manifest=manifest, fingerprint=fingerprint)


def plan_compaction(paths: Sequence[Path]) -> CompactionPlan:
    valid_by_run: dict[str, ValidBundle] = {}
    rejected: list[dict] = []
    for path in sorted(set(paths), key=lambda item: str(item)):
        try:
            bundle = validate_bundle(path)
        except InvalidBundle as exc:
            rejected.append({"path": str(path), "reason": str(exc)})
            continue
        existing = valid_by_run.get(bundle.run_id)
        if existing and existing.path != bundle.path:
            rejected.append({"path": str(path), "reason": f"duplicate run_id {bundle.run_id}"})
            continue
        valid_by_run[bundle.run_id] = bundle

    # Exactly one deterministic attempt per logical digest is accepted.
    by_digest: dict[str, ValidBundle] = {}
    for bundle in valid_by_run.values():
        current = by_digest.get(bundle.digest_at)
        if current is None or bundle.order_key > current.order_key:
            by_digest[bundle.digest_at] = bundle
    accepted = tuple(sorted(by_digest.values(), key=lambda bundle: bundle.order_key))
    latest = accepted[-1] if accepted else None
    identity_payload = {
        "accepted": [f"{bundle.run_id}:{bundle.fingerprint}" for bundle in accepted],
        "rejected": [
            {"bundle": Path(item["path"]).name, "reason": item["reason"]} for item in rejected
        ],
    }
    identity = json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    generation = hashlib.sha256(identity).hexdigest()[:20]
    return CompactionPlan(accepted, latest, tuple(rejected), generation)


def _master_rows(bundle: ValidBundle) -> Iterator[dict[str, str]]:
    path = bundle.path / "candidates" / "master_ref.csv"
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            index_id = str(row.get("index_id") or "").strip()
            if index_id:
                yield {column: str(row.get(column) or "") for column in MASTER_COLUMNS}


def compact_master(accepted: Iterable[ValidBundle]) -> list[dict[str, str]]:
    rows: dict[str, tuple[tuple[str, str, str], dict[str, str]]] = {}
    first_seen: dict[str, str] = {}
    last_seen: dict[str, str] = {}
    for bundle in accepted:
        for row in _master_rows(bundle):
            index_id = row["index_id"]
            first = row.get("first_seen") or ""
            last = row.get("last_seen") or ""
            if first and (not first_seen.get(index_id) or first < first_seen[index_id]):
                first_seen[index_id] = first
            if last and (not last_seen.get(index_id) or last > last_seen[index_id]):
                last_seen[index_id] = last
            rank = (last, bundle.digest_at, bundle.run_id)
            if index_id not in rows or rank > rows[index_id][0]:
                rows[index_id] = (rank, row)
    output: list[dict[str, str]] = []
    for index_id in sorted(rows):
        row = dict(rows[index_id][1])
        row["first_seen"] = first_seen.get(index_id, row.get("first_seen", ""))
        row["last_seen"] = last_seen.get(index_id, row.get("last_seen", ""))
        output.append(row)
    return output


def _write_jsonl(path: Path, source: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        path.write_text("", encoding="utf-8")
        return
    # Parse every line so malformed candidate content cannot become canonical.
    lines: list[str] = []
    with source.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                lines.append(json.dumps(json.loads(line), ensure_ascii=False, sort_keys=True))
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def build_generation(plan: CompactionPlan, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "master_ref.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MASTER_COLUMNS)
        writer.writeheader()
        writer.writerows(compact_master(plan.accepted))
    latest = plan.latest
    _write_jsonl(
        destination / "news_recent_refs.jsonl",
        latest.path / "candidates" / "news_recent_refs.jsonl" if latest else None,
    )
    _write_jsonl(
        destination / "news_recent_groups.jsonl",
        latest.path / "candidates" / "news_recent_groups.jsonl" if latest else None,
    )
    accepted_payload = [
        {"run_id": bundle.run_id, "digest_at": bundle.digest_at, "status": bundle.manifest["status"]}
        for bundle in plan.accepted
    ]
    (destination / "accepted_runs.json").write_text(
        json.dumps(accepted_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    lane_status = {
        "schema_version": "sensing_compacted_status.v1",
        "generation": plan.generation,
        "last_run_id": latest.run_id if latest else None,
        "last_digest_at": latest.digest_at if latest else None,
        "last_status": latest.manifest["status"] if latest else "empty",
        "accepted_run_count": len(plan.accepted),
        "rejected": list(plan.rejected),
    }
    (destination / "lane_status.json").write_text(
        json.dumps(lane_status, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    files = sorted(path for path in destination.iterdir() if path.is_file())
    manifest = {
        "schema_version": "sensing_compaction.v1",
        "generation": plan.generation,
        "accepted_run_ids": [bundle.run_id for bundle in plan.accepted],
        "latest_run_id": latest.run_id if latest else None,
        "checksums": {path.name: sha256_file(path) for path in files},
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, sort_keys=True, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


@contextmanager
def single_writer_lock(state_root: Path) -> Iterator[None]:
    state_root.mkdir(parents=True, exist_ok=True)
    with (state_root / ".compactor.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def publish_compaction(run_root: Path, state_root: Path, paths: Sequence[Path] | None = None) -> Path:
    """Publish one immutable generation, then atomically select it via current.json."""
    with single_writer_lock(state_root):
        plan = plan_compaction(paths if paths is not None else discover_bundles(run_root))
        generations = state_root / "generations"
        generation = generations / plan.generation
        if not generation.exists():
            generations.mkdir(parents=True, exist_ok=True)
            staging = state_root / ".staging" / plan.generation
            if staging.exists():
                shutil.rmtree(staging)
            staging.parent.mkdir(parents=True, exist_ok=True)
            build_generation(plan, staging)
            staging.rename(generation)
        current_path = state_root / "current.json"
        if current_path.exists():
            try:
                current = json.loads(current_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if current.get("generation") == plan.generation:
                return generation
        pointer = {
            "schema_version": "sensing_compaction_pointer.v1",
            "generation": plan.generation,
            "generation_path": str(generation),
            "latest_run_id": plan.latest.run_id if plan.latest else None,
            "latest_digest_at": plan.latest.digest_at if plan.latest else None,
            "updated_at": utc_now_iso(),
        }
        _atomic_json(current_path, pointer)
        return generation
