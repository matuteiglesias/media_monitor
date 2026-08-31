from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "contracts" / "schemas"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_name(value: str) -> str:
    return sha256_text(value)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate(schema_name: str, payload: dict) -> None:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"{schema_name} validation failed: " + "; ".join(error.message for error in errors[:5]))


def _write_json_once(path: Path, payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"immutable artifact collision at {path}")
        return
    path.write_text(text, encoding="utf-8")


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class MediaObservation:
    source_id: str
    video_id: str
    title: str
    description: str
    published_at: str
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    availability: str
    observed_at: str

    @property
    def item_uid(self) -> str:
        return f"youtube:{self.video_id}"


@dataclass(frozen=True)
class ItemResult:
    item_uid: str
    state: str
    snapshot_id: str


@dataclass(frozen=True)
class MaterializationSummary:
    observations: int
    new_items: int
    new_snapshots: int
    unchanged_snapshots: int
    metadata_mutations: int
    failures: int


class MediaWatchStore:
    """Filesystem state owned only by the monitored-media lane."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.items_dir = root / "items"
        self.snapshots_dir = root / "snapshots"
        self.sources_dir = root / "sources"
        self.runs_dir = root / "runs"

    def item_path(self, item_uid: str) -> Path:
        return self.items_dir / f"{safe_name(item_uid)}.json"

    def snapshot_dir(self, item_uid: str) -> Path:
        return self.snapshots_dir / safe_name(item_uid)

    def source_path(self, source_id: str) -> Path:
        return self.sources_dir / f"{safe_name(source_id)}.json"

    def load_item(self, item_uid: str) -> dict | None:
        path = self.item_path(item_uid)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def list_items(self) -> list[dict]:
        if not self.items_dir.exists():
            return []
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in self.items_dir.glob("*.json")]
        return sorted(rows, key=lambda row: (row["published_at"], row["item_uid"]), reverse=True)

    def list_snapshots(self, item_uid: str | None = None) -> list[dict]:
        if not self.snapshots_dir.exists():
            return []
        paths = self.snapshot_dir(item_uid).glob("*.json") if item_uid else self.snapshots_dir.glob("*/*.json")
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        return sorted(rows, key=lambda row: (row["observed_at"], row["snapshot_id"]), reverse=True)

    def load_source_state(self, source_id: str) -> dict | None:
        path = self.source_path(source_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def list_source_states(self) -> list[dict]:
        if not self.sources_dir.exists():
            return []
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in self.sources_dir.glob("*.json")]
        return sorted(rows, key=lambda row: row["source_id"])

    @staticmethod
    def _snapshot_payload(observation: MediaObservation) -> dict:
        return {"title": observation.title, "description": observation.description, "statistics": {"view_count": observation.view_count, "like_count": observation.like_count, "comment_count": observation.comment_count}, "availability": observation.availability}

    def ingest(self, observation: MediaObservation) -> ItemResult:
        item_uid = observation.item_uid
        existing = self.load_item(item_uid)
        payload = self._snapshot_payload(observation)
        payload_sha = sha256_text(canonical_json(payload))
        snapshot_id = f"media-snapshot:{sha256_text(canonical_json({'item_uid': item_uid, 'payload_sha256': payload_sha}))[:32]}"
        snapshot_path = self.snapshot_dir(item_uid) / f"{safe_name(snapshot_id)}.json"
        new_snapshot = not snapshot_path.exists()
        if new_snapshot:
            snapshot = {"schema_name": "media_metadata_snapshot.v1", "schema_status": "experimental", "snapshot_id": snapshot_id, "item_uid": item_uid, "observed_at": observation.observed_at, **payload, "payload_sha256": payload_sha}
            _validate("media_metadata_snapshot.v1.json", snapshot)
            _write_json_once(snapshot_path, snapshot)
        item = {"schema_name": "media_item.v1", "schema_status": "experimental", "item_uid": item_uid, "source_id": observation.source_id, "platform": "youtube", "native_id": observation.video_id, "canonical_url": f"https://www.youtube.com/watch?v={observation.video_id}", "title": observation.title, "description": observation.description, "published_at": observation.published_at, "duration_seconds": observation.duration_seconds, "first_seen": existing["first_seen"] if existing else observation.observed_at, "last_seen": observation.observed_at}
        _validate("media_item.v1.json", item)
        _write_json_atomic(self.item_path(item_uid), item)
        state = "first_seen" if existing is None else "metadata_mutation" if new_snapshot else "unchanged"
        return ItemResult(item_uid, state, snapshot_id)

    def update_source_state(self, *, source_id: str, display_name: str, channel_id: str, channel_title: str, uploads_playlist_id: str, observed_at: str, latest_published_at: str | None, health: str, error: str | None, item_count: int, api_calls: int, quota_units_estimated: int) -> dict:
        previous = self.load_source_state(source_id)
        state = {"schema_name": "media_source_state.m1.v1", "source_id": source_id, "display_name": display_name, "channel_id": channel_id, "channel_title": channel_title, "uploads_playlist_id": uploads_playlist_id, "last_attempt_at": observed_at, "last_success_at": observed_at if health == "healthy" else (previous or {}).get("last_success_at"), "latest_published_at": latest_published_at, "health": health, "error": error, "item_count": item_count, "api_calls": api_calls, "quota_units_estimated": quota_units_estimated}
        _write_json_atomic(self.source_path(source_id), state)
        return state

    def materialize(self, observations: Sequence[MediaObservation]) -> tuple[MaterializationSummary, list[dict], str]:
        results: list[ItemResult] = []
        failures: list[dict] = []
        seen: set[str] = set()
        for observation in observations:
            if observation.item_uid in seen:
                failures.append({"item_uid": observation.item_uid, "error_type": "DuplicateItemUid"})
                continue
            seen.add(observation.item_uid)
            try:
                results.append(self.ingest(observation))
            except Exception as exc:
                failures.append({"item_uid": observation.item_uid, "error_type": type(exc).__name__, "message": str(exc)})
        summary = MaterializationSummary(observations=len(observations), new_items=sum(result.state == "first_seen" for result in results), new_snapshots=sum(result.state in {"first_seen", "metadata_mutation"} for result in results), unchanged_snapshots=sum(result.state == "unchanged" for result in results), metadata_mutations=sum(result.state == "metadata_mutation" for result in results), failures=len(failures))
        evidence = [asdict(row) for row in observations]
        evidence_id = "media-evidence:" + sha256_text(canonical_json({"observations": evidence, "failures": failures}))[:24]
        run_id = "media-run:" + sha256_text(canonical_json({"evidence_id": evidence_id, "summary": asdict(summary)}))[:24]
        _write_json_once(self.runs_dir / safe_name(run_id) / "run_manifest.json", {"schema_name": "media_materialization_run.m1.v1", "run_id": run_id, "evidence_id": evidence_id, **asdict(summary)})
        return summary, failures, run_id

    def snapshot_count(self) -> int:
        return len(self.list_snapshots())
