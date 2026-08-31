from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .enrichment import MediaEnrichmentStore, load_watch_config, search_store
from .store import MediaWatchStore

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "media_watch" / "sources.yaml"


class MediaWatchReadModel:
    def __init__(self, store: MediaWatchStore, config_path: Path = DEFAULT_CONFIG) -> None:
        self.store = store
        self.enrichment = MediaEnrichmentStore(store)
        self.config = load_watch_config(config_path)
        self.people_config = self.config["watch"].get("people", [])

    def overview(self) -> dict:
        sources = self.store.list_source_states()
        text_assets = self.enrichment.list_text_assets()
        appearances = self.enrichment.list_appearances()
        return {
            "schema_name": "media_intelligence_overview.m4.v1",
            "source_count": len(sources),
            "item_count": len(self.store.list_items()),
            "snapshot_count": self.store.snapshot_count(),
            "text_asset_count": len(text_assets),
            "segment_count": len(self.enrichment.list_segments()),
            "appearance_count": len(appearances),
            "person_count": len(self.people_config),
            "sources": sources,
            "text_enrichment": "governed_m2" if text_assets else "not_attempted_m1",
        }

    def outlets(self) -> dict:
        rows = []
        for source in self.store.list_source_states():
            items = [item for item in self.store.list_items() if item["source_id"] == source["source_id"]]
            with_text = sum(self.enrichment.text_status(item["item_uid"])["available"] for item in items)
            rows.append({**source, "text_available_count": with_text, "text_coverage": (with_text / len(items)) if items else 0.0})
        return {"outlets": rows}

    def items(self, *, source_id: str | None = None, limit: int = 50) -> dict:
        source_by_id = {row["source_id"]: row for row in self.store.list_source_states()}
        rows = []
        for item in self.store.list_items():
            if source_id and item["source_id"] != source_id:
                continue
            text_state = self.enrichment.text_status(item["item_uid"])
            rows.append({
                **item,
                "outlet": source_by_id.get(item["source_id"]),
                "text_status": text_state["status"],
                "text_available": text_state["available"],
                "appearance_count": len(self.enrichment.list_appearances(item_uid=item["item_uid"])),
                "segment_count": len(self.enrichment.list_segments(item["item_uid"])),
            })
            if len(rows) >= limit:
                break
        return {"items": rows, "count": len(rows)}

    def item(self, native_id: str) -> dict | None:
        item = self.store.load_item(f"youtube:{native_id}")
        if item is None:
            return None
        source = self.store.load_source_state(item["source_id"])
        snapshots = self.store.list_snapshots(item["item_uid"])
        text_state = self.enrichment.text_status(item["item_uid"])
        text_assets = self.enrichment.list_text_assets(item["item_uid"])
        segments = self.enrichment.list_segments(item["item_uid"])
        appearances = self.enrichment.list_appearances(item_uid=item["item_uid"])
        if text_state["status"] == "not_attempted":
            text_enrichment = {"status": "not_attempted_m1", "available": False, "message": "No governed text acquisition has been attempted for this item."}
        else:
            text_enrichment = {"status": text_state["status"], "available": text_state["available"], "message": "Text state is explicit producer evidence; unavailable/blocked states are not monitoring failures."}
        return {
            "item": item,
            "outlet": source,
            "metadata_snapshots": snapshots,
            "snapshot_count": len(snapshots),
            "text_enrichment": text_enrichment,
            "text_assets": text_assets,
            "segments": segments,
            "appearances": appearances,
        }

    def people(self) -> dict:
        rows = []
        for person in self.people_config:
            appearances = self.enrichment.list_appearances(person_id=person["person_id"])
            source_ids: set[str] = set()
            for appearance in appearances:
                item = self.store.load_item(appearance["item_uid"])
                if item:
                    source_ids.add(item["source_id"])
            rows.append({**person, "appearance_count": len(appearances), "outlet_count": len(source_ids)})
        return {"people": rows}

    def person(self, person_id: str) -> dict | None:
        person = next((row for row in self.people_config if row["person_id"] == person_id), None)
        if person is None:
            return None
        source_by_id = {row["source_id"]: row for row in self.store.list_source_states()}
        rows = []
        for appearance in self.enrichment.list_appearances(person_id=person_id):
            item = self.store.load_item(appearance["item_uid"])
            if item is None:
                continue
            rows.append({"appearance": appearance, "item": item, "outlet": source_by_id.get(item["source_id"])})
        rows.sort(key=lambda row: (row["item"]["published_at"], row["appearance"]["appearance_id"]), reverse=True)
        return {"person": person, "appearances": rows, "appearance_count": len(rows)}

    def search(self, query: str, *, limit: int = 50) -> dict:
        source_by_id = {row["source_id"]: row for row in self.store.list_source_states()}
        hits = search_store(self.enrichment, query, limit=limit)
        return {
            "query": query,
            "capability": "metadata_and_governed_text_literal_match",
            "hits": [{**hit, "outlet": source_by_id.get(hit["source_id"])} for hit in hits],
            "count": len(hits),
        }


def serve(*, store_root: Path, host: str, port: int, config_path: Path = DEFAULT_CONFIG) -> None:
    model = MediaWatchReadModel(MediaWatchStore(store_root), config_path=config_path)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: object, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send({"status": "ok"}); return
            if parsed.path == "/api/channel-monitor":
                self._send(model.overview()); return
            if parsed.path == "/api/outlets":
                self._send(model.outlets()); return
            if parsed.path == "/api/people":
                self._send(model.people()); return
            if parsed.path == "/api/search":
                query = parse_qs(parsed.query)
                q = (query.get("q") or [""])[0]
                try:
                    limit = min(100, max(1, int((query.get("limit") or ["50"])[0])))
                except ValueError:
                    self._send({"error": "invalid limit"}, HTTPStatus.BAD_REQUEST); return
                self._send(model.search(q, limit=limit)); return
            if parsed.path == "/api/items":
                query = parse_qs(parsed.query); source_id = (query.get("source_id") or [None])[0]
                try:
                    limit = min(100, max(1, int((query.get("limit") or ["50"])[0])))
                except ValueError:
                    self._send({"error": "invalid limit"}, HTTPStatus.BAD_REQUEST); return
                self._send(model.items(source_id=source_id, limit=limit)); return
            people_prefix = "/api/people/"
            if parsed.path.startswith(people_prefix):
                payload = model.person(unquote(parsed.path[len(people_prefix):]))
                self._send(payload if payload is not None else {"error": "not found"}, HTTPStatus.OK if payload is not None else HTTPStatus.NOT_FOUND); return
            item_prefix = "/api/items/"
            if parsed.path.startswith(item_prefix):
                payload = model.item(unquote(parsed.path[len(item_prefix):]))
                self._send(payload if payload is not None else {"error": "not found"}, HTTPStatus.OK if payload is not None else HTTPStatus.NOT_FOUND); return
            self._send({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve read-only Media Intelligence Workbench API")
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args(argv)
    serve(store_root=args.store_root, host=args.host, port=args.port, config_path=args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
