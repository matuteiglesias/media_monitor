from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .store import MediaWatchStore


class MediaWatchReadModel:
    def __init__(self, store: MediaWatchStore) -> None:
        self.store = store

    def overview(self) -> dict:
        sources = self.store.list_source_states()
        return {"schema_name": "channel_monitor_overview.m1.v1", "source_count": len(sources), "item_count": len(self.store.list_items()), "snapshot_count": self.store.snapshot_count(), "sources": sources, "text_enrichment": "not_attempted_m1"}

    def outlets(self) -> dict:
        return {"outlets": self.store.list_source_states()}

    def items(self, *, source_id: str | None = None, limit: int = 50) -> dict:
        source_by_id = {row["source_id"]: row for row in self.store.list_source_states()}
        rows = []
        for item in self.store.list_items():
            if source_id and item["source_id"] != source_id:
                continue
            rows.append({**item, "outlet": source_by_id.get(item["source_id"]), "text_enrichment": "not_attempted_m1"})
            if len(rows) >= limit:
                break
        return {"items": rows, "count": len(rows)}

    def item(self, native_id: str) -> dict | None:
        item = self.store.load_item(f"youtube:{native_id}")
        if item is None:
            return None
        source = self.store.load_source_state(item["source_id"])
        snapshots = self.store.list_snapshots(item["item_uid"])
        return {"item": item, "outlet": source, "metadata_snapshots": snapshots, "snapshot_count": len(snapshots), "text_enrichment": {"status": "not_attempted_m1", "message": "M1 monitors publisher metadata only; text enrichment is a later governed lane."}}


def serve(*, store_root: Path, host: str, port: int) -> None:
    model = MediaWatchReadModel(MediaWatchStore(store_root))
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
            if parsed.path == "/healthz": self._send({"status": "ok"}); return
            if parsed.path == "/api/channel-monitor": self._send(model.overview()); return
            if parsed.path == "/api/outlets": self._send(model.outlets()); return
            if parsed.path == "/api/items":
                query = parse_qs(parsed.query); source_id = (query.get("source_id") or [None])[0]
                try: limit = min(100, max(1, int((query.get("limit") or ["50"])[0])))
                except ValueError: self._send({"error": "invalid limit"}, HTTPStatus.BAD_REQUEST); return
                self._send(model.items(source_id=source_id, limit=limit)); return
            prefix = "/api/items/"
            if parsed.path.startswith(prefix):
                payload = model.item(unquote(parsed.path[len(prefix):]))
                self._send(payload if payload is not None else {"error": "not found"}, HTTPStatus.OK if payload is not None else HTTPStatus.NOT_FOUND); return
            self._send({"error": "not found"}, HTTPStatus.NOT_FOUND)
        def log_message(self, format: str, *args: object) -> None: return
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve read-only Channel Monitor M1 API")
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args(argv)
    serve(store_root=args.store_root, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
