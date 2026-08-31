from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import yaml

from .store import MediaWatchStore, _validate, _write_json_atomic, _write_json_once, canonical_json, safe_name, sha256_text

AVAILABLE_TEXT_STATUSES = {
    "publisher_transcript",
    "publisher_caption_authorized",
    "publisher_article_text",
    "operator_supplied_transcript",
    "authorized_asr",
}


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _read_rows(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in directory.glob("*.json")]


class MediaEnrichmentStore:
    """Producer-owned governed derivatives for monitored media.

    This store does not acquire arbitrary third-party text. Callers must select an
    allowed provenance state explicitly before materializing a text asset.
    """

    def __init__(self, store: MediaWatchStore) -> None:
        self.store = store
        self.root = store.root
        self.text_assets_dir = self.root / "text_assets"
        self.segments_dir = self.root / "segments"
        self.appearances_dir = self.root / "appearances"
        self.indexes_dir = self.root / "indexes"

    def list_text_assets(self, item_uid: str | None = None) -> list[dict]:
        rows = _read_rows(self.text_assets_dir)
        if item_uid:
            rows = [row for row in rows if row["item_uid"] == item_uid]
        return sorted(rows, key=lambda row: (row["observed_at"], row["text_asset_id"]), reverse=True)

    def list_segments(self, item_uid: str | None = None) -> list[dict]:
        rows = _read_rows(self.segments_dir)
        if item_uid:
            rows = [row for row in rows if row["item_uid"] == item_uid]
        return sorted(rows, key=lambda row: (row["item_uid"], row["start_seconds"], row["segment_id"]))

    def list_appearances(self, *, item_uid: str | None = None, person_id: str | None = None) -> list[dict]:
        rows = _read_rows(self.appearances_dir)
        if item_uid:
            rows = [row for row in rows if row["item_uid"] == item_uid]
        if person_id:
            rows = [row for row in rows if row["person_id"] == person_id]
        return sorted(rows, key=lambda row: (row["observed_at"], row["appearance_id"]), reverse=True)

    def put_text_asset(
        self,
        *,
        item_uid: str,
        status: str,
        acquisition_method: str,
        observed_at: str,
        text: str | None = None,
        language: str | None = None,
        timing_available: bool = False,
        generator: dict | None = None,
    ) -> dict:
        if self.store.load_item(item_uid) is None:
            raise ValueError(f"unknown item {item_uid}")
        text_sha = sha256_text(text) if text is not None else None
        semantic = {
            "item_uid": item_uid,
            "status": status,
            "acquisition_method": acquisition_method,
            "language": language,
            "timing_available": timing_available,
            "text_sha256": text_sha,
            "generator": generator,
        }
        asset_id = f"media-text:{sha256_text(canonical_json(semantic))[:32]}"
        path = self.text_assets_dir / f"{safe_name(asset_id)}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        payload = {
            "schema_name": "media_text_asset.v1",
            "schema_status": "experimental",
            "text_asset_id": asset_id,
            "item_uid": item_uid,
            "status": status,
            "acquisition_method": acquisition_method,
            "language": language,
            "timing_available": timing_available,
            "text": text,
            "text_sha256": text_sha,
            "observed_at": observed_at,
            "generator": generator,
        }
        _validate("media_text_asset.v1.json", payload)
        _write_json_once(path, payload)
        return payload

    def put_segment(
        self,
        *,
        item_uid: str,
        start_seconds: float,
        end_seconds: float,
        boundary_source: str,
        label: str | None = None,
        text_asset_id: str | None = None,
        confidence: float | None = None,
    ) -> dict:
        if self.store.load_item(item_uid) is None:
            raise ValueError(f"unknown item {item_uid}")
        if end_seconds <= start_seconds:
            raise ValueError("segment end must be after start")
        semantic = {
            "item_uid": item_uid,
            "start_seconds": float(start_seconds),
            "end_seconds": float(end_seconds),
            "boundary_source": boundary_source,
            "label": label,
            "text_asset_id": text_asset_id,
        }
        segment_id = f"media-segment:{sha256_text(canonical_json(semantic))[:32]}"
        payload = {
            "schema_name": "media_segment.v1",
            "schema_status": "experimental",
            "segment_id": segment_id,
            "item_uid": item_uid,
            "start_seconds": float(start_seconds),
            "end_seconds": float(end_seconds),
            "boundary_source": boundary_source,
            "label": label,
            "text_asset_id": text_asset_id,
            "confidence": confidence,
        }
        _validate("media_segment.v1.json", payload)
        _write_json_once(self.segments_dir / f"{safe_name(segment_id)}.json", payload)
        return payload

    def ensure_whole_item_segment(self, item: dict) -> dict:
        duration = item.get("duration_seconds")
        end = float(duration) if duration and duration > 0 else 1.0
        return self.put_segment(
            item_uid=item["item_uid"],
            start_seconds=0.0,
            end_seconds=end,
            boundary_source="whole_item",
            label="Whole item",
        )

    def put_appearance(
        self,
        *,
        person_id: str,
        item_uid: str,
        segment_id: str | None,
        evidence_source: str,
        matched_alias: str,
        observed_at: str,
        confidence: float | None = None,
    ) -> dict:
        semantic = {
            "person_id": person_id,
            "item_uid": item_uid,
            "segment_id": segment_id,
            "evidence_source": evidence_source,
            "matched_alias": matched_alias,
        }
        appearance_id = f"media-appearance:{sha256_text(canonical_json(semantic))[:32]}"
        path = self.appearances_dir / f"{safe_name(appearance_id)}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        payload = {
            "schema_name": "media_appearance.v1",
            "schema_status": "experimental",
            "appearance_id": appearance_id,
            "person_id": person_id,
            "item_uid": item_uid,
            "segment_id": segment_id,
            "evidence_source": evidence_source,
            "matched_alias": matched_alias,
            "confidence": confidence,
            "observed_at": observed_at,
        }
        _validate("media_appearance.v1.json", payload)
        _write_json_once(path, payload)
        return payload

    def text_status(self, item_uid: str) -> dict:
        assets = self.list_text_assets(item_uid)
        if not assets:
            return {"status": "not_attempted", "available": False, "asset": None}
        asset = assets[0]
        return {"status": asset["status"], "available": asset["status"] in AVAILABLE_TEXT_STATUSES, "asset": asset}

    def write_indexes(self, people: list[dict]) -> dict:
        source_by_id = {row["source_id"]: row for row in self.store.list_source_states()}
        appearances = self.list_appearances()
        appearance_by_item: dict[str, list[dict]] = {}
        for row in appearances:
            appearance_by_item.setdefault(row["item_uid"], []).append(row)
        latest = []
        text_rows = []
        for item in self.store.list_items():
            text_state = self.text_status(item["item_uid"])
            latest.append({
                **item,
                "outlet": source_by_id.get(item["source_id"]),
                "text_status": text_state["status"],
                "appearance_count": len(appearance_by_item.get(item["item_uid"], [])),
            })
            text_rows.append({"item_uid": item["item_uid"], "status": text_state["status"], "available": text_state["available"]})
        person_rows = []
        for person in people:
            rows = [row for row in appearances if row["person_id"] == person["person_id"]]
            person_rows.append({**person, "appearance_count": len(rows), "outlet_count": len({self.store.load_item(row["item_uid"])["source_id"] for row in rows if self.store.load_item(row["item_uid"])})})
        indexes = {
            "latest_items.json": latest,
            "outlets.json": self.store.list_source_states(),
            "people.json": person_rows,
            "appearances.json": appearances,
            "text_status.json": text_rows,
            "health.json": {"sources": self.store.list_source_states()},
        }
        for name, payload in indexes.items():
            _write_json_atomic(self.indexes_dir / name, {"generated_from_store": True, "rows": payload} if isinstance(payload, list) else payload)
        return {"index_names": sorted(indexes), "item_count": len(latest), "appearance_count": len(appearances)}


def parse_description_timestamps(description: str, *, duration_seconds: int | None) -> list[tuple[float, float, str]]:
    def seconds(token: str) -> int:
        parts = [int(part) for part in token.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0] * 3600 + parts[1] * 60 + parts[2]

    matches: list[tuple[int, str]] = []
    for match in re.finditer(r"(?m)^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+(.+?)\s*$", description):
        start = seconds(match.group(1))
        if duration_seconds is not None and start >= duration_seconds:
            continue
        matches.append((start, match.group(2).strip()))
    unique = sorted(dict(matches).items())
    result: list[tuple[float, float, str]] = []
    for index, (start, label) in enumerate(unique):
        next_start = unique[index + 1][0] if index + 1 < len(unique) else duration_seconds
        if next_start is None or next_start <= start:
            continue
        result.append((float(start), float(next_start), label))
    return result


def materialize_segments(enrichment: MediaEnrichmentStore) -> int:
    created = 0
    for item in enrichment.store.list_items():
        before = len(enrichment.list_segments(item["item_uid"]))
        enrichment.ensure_whole_item_segment(item)
        for start, end, label in parse_description_timestamps(item.get("description") or "", duration_seconds=item.get("duration_seconds")):
            enrichment.put_segment(
                item_uid=item["item_uid"],
                start_seconds=start,
                end_seconds=end,
                boundary_source="description_timestamp",
                label=label,
            )
        created += max(0, len(enrichment.list_segments(item["item_uid"])) - before)
    return created


def load_watch_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return config


def detect_appearances(enrichment: MediaEnrichmentStore, people: list[dict]) -> list[dict]:
    created: list[dict] = []
    for item in enrichment.store.list_items():
        whole = enrichment.ensure_whole_item_segment(item)
        title_fold = fold_text(item.get("title") or "")
        description_fold = fold_text(item.get("description") or "")
        text_assets = [row for row in enrichment.list_text_assets(item["item_uid"]) if row["status"] in AVAILABLE_TEXT_STATUSES and row.get("text")]
        for person in people:
            matched: tuple[str, str] | None = None
            for alias in person["aliases"]:
                needle = fold_text(alias)
                if needle and needle in title_fold:
                    matched = ("title", alias)
                    break
            if matched is None:
                for alias in person["aliases"]:
                    needle = fold_text(alias)
                    if needle and needle in description_fold:
                        matched = ("description", alias)
                        break
            if matched is None:
                for asset in text_assets:
                    body = fold_text(asset.get("text") or "")
                    for alias in person["aliases"]:
                        needle = fold_text(alias)
                        if needle and needle in body:
                            matched = ("transcript", alias)
                            break
                    if matched:
                        break
            if matched:
                created.append(enrichment.put_appearance(
                    person_id=person["person_id"],
                    item_uid=item["item_uid"],
                    segment_id=whole["segment_id"],
                    evidence_source=matched[0],
                    matched_alias=matched[1],
                    observed_at=item["last_seen"],
                    confidence=1.0,
                ))
    return created


def search_store(enrichment: MediaEnrichmentStore, query: str, *, limit: int = 50) -> list[dict]:
    needle = fold_text(query.strip())
    if not needle:
        return []
    hits: list[dict] = []
    for item in enrichment.store.list_items():
        evidence: list[dict] = []
        if needle in fold_text(item.get("title") or ""):
            evidence.append({"source": "title", "text_asset_id": None})
        if needle in fold_text(item.get("description") or ""):
            evidence.append({"source": "description", "text_asset_id": None})
        for asset in enrichment.list_text_assets(item["item_uid"]):
            if asset["status"] in AVAILABLE_TEXT_STATUSES and asset.get("text") and needle in fold_text(asset["text"]):
                evidence.append({"source": "text_asset", "text_asset_id": asset["text_asset_id"], "status": asset["status"]})
        if evidence:
            hits.append({"item_uid": item["item_uid"], "native_id": item["native_id"], "title": item["title"], "published_at": item["published_at"], "source_id": item["source_id"], "evidence": evidence})
        if len(hits) >= limit:
            break
    return hits
