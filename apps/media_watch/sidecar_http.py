from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import requests

from .sidecar import build_sidecar, ensure_video_sidecar
from .store import MediaWatchStore
from .summary import DEFAULT_GEMINI_MODEL, GeminiSummaryProvider
from .youtube_api import YouTubeDataClient

ENSURE_PATH = "/v1/youtube/videos/ensure"
INSPECT_PATH = "/v1/youtube/videos/inspect"
SUMMARY_PATH = "/v1/youtube/videos/summary"
MAX_REQUEST_BYTES = 4096
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
LOGGER = logging.getLogger("media_watch.youtube_sidecar_http")


@dataclass(frozen=True)
class BridgeResponse:
    status: int
    payload: dict


class BridgeError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def response(self) -> BridgeResponse:
        return BridgeResponse(
            self.status,
            {
                "error": {
                    "code": self.code,
                    "message": self.message,
                }
            },
        )


MetadataClientFactory = Callable[[], YouTubeDataClient | None]
SummaryProviderFactory = Callable[[], GeminiSummaryProvider | None]


def _metadata_client_from_env() -> YouTubeDataClient | None:
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    return YouTubeDataClient(api_key) if api_key else None


def _summary_provider_from_env() -> GeminiSummaryProvider | None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = (os.environ.get("GEMINI_MODEL", "") or DEFAULT_GEMINI_MODEL).strip()
    return GeminiSummaryProvider(api_key=api_key, model=model)


def _configured_store_root() -> Path:
    configured = os.environ.get("MEDIA_WATCH_STORE_ROOT", "").strip()
    if configured:
        return Path(configured)
    if os.environ.get("K_SERVICE", "").strip():
        raise RuntimeError(
            "MEDIA_WATCH_STORE_ROOT is required on Cloud Run; "
            "the container filesystem is not an authoritative Media Watch store"
        )
    return Path("data/canonical/media_watch")


class YouTubeSidecarBridge:
    """Small HTTP-facing projection over the existing governed YouTube sidecar."""

    def __init__(
        self,
        store: MediaWatchStore,
        *,
        metadata_client_factory: MetadataClientFactory = _metadata_client_from_env,
        summary_provider_factory: SummaryProviderFactory = _summary_provider_from_env,
    ) -> None:
        self.store = store
        self.metadata_client_factory = metadata_client_factory
        self.summary_provider_factory = summary_provider_factory
        # MediaWatchStore is filesystem-backed and not a transactional multi-writer store.
        # Serialize bridge mutations inside one process; deployment keeps one instance/concurrency.
        self._mutation_lock = threading.RLock()

    @staticmethod
    def _video_id(payload: object) -> str:
        if not isinstance(payload, dict) or set(payload) != {"video_id"}:
            raise BridgeError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request",
                "Request body must contain only video_id",
            )
        video_id = payload.get("video_id")
        if not isinstance(video_id, str) or not _VIDEO_ID_RE.fullmatch(video_id):
            raise BridgeError(
                HTTPStatus.BAD_REQUEST,
                "invalid_video_id",
                "video_id must be an 11-character YouTube video ID",
            )
        return video_id

    def post(self, path: str, payload: object) -> BridgeResponse:
        try:
            video_id = self._video_id(payload)
            if path == ENSURE_PATH:
                return BridgeResponse(HTTPStatus.OK, self._ensure(video_id))
            if path == INSPECT_PATH:
                return BridgeResponse(HTTPStatus.OK, self._inspect(video_id))
            if path == SUMMARY_PATH:
                return BridgeResponse(HTTPStatus.OK, self._summary(video_id))
            raise BridgeError(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")
        except BridgeError as exc:
            self._log_result(path=path, status=exc.status, code=exc.code)
            return exc.response()
        except Exception as exc:
            self._log_exception(path, "internal_error", exc)
            return BridgeError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                "Media Monitor could not complete the request",
            ).response()

    def _ensure(self, video_id: str) -> dict:
        item_uid = f"youtube:{video_id}"
        with self._mutation_lock:
            metadata_client = None
            if self.store.load_item(item_uid) is None:
                metadata_client = self.metadata_client_factory()
                if metadata_client is None:
                    raise BridgeError(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "metadata_provider_unconfigured",
                        "Video metadata provider is unavailable",
                    )
            try:
                payload = ensure_video_sidecar(
                    self.store,
                    video_id,
                    metadata_client=metadata_client,
                )
            except LookupError as exc:
                self._log_exception(ENSURE_PATH, "video_not_found", exc)
                raise BridgeError(
                    HTTPStatus.NOT_FOUND,
                    "video_not_found",
                    "YouTube video was not found",
                ) from None
            except requests.Timeout as exc:
                self._log_exception(ENSURE_PATH, "metadata_provider_timeout", exc)
                raise BridgeError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "metadata_provider_timeout",
                    "Video metadata provider timed out",
                ) from None
            except requests.RequestException as exc:
                self._log_exception(ENSURE_PATH, "metadata_provider_error", exc)
                raise BridgeError(
                    HTTPStatus.BAD_GATEWAY,
                    "metadata_provider_error",
                    "Video metadata provider failed",
                ) from None
            except Exception as exc:
                self._log_exception(ENSURE_PATH, "internal_error", exc)
                raise BridgeError(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "internal_error",
                    "Media Monitor could not ensure the video",
                ) from None
        self._log_result(path=ENSURE_PATH, status=HTTPStatus.OK, code="ok", video_id=video_id)
        return payload

    def _inspect(self, video_id: str) -> dict:
        if self.store.load_item(f"youtube:{video_id}") is None:
            raise BridgeError(
                HTTPStatus.NOT_FOUND,
                "video_not_found",
                "Video is not present in governed Media Monitor state",
            )
        try:
            payload = build_sidecar(self.store, video_id)
        except Exception as exc:
            self._log_exception(INSPECT_PATH, "internal_error", exc)
            raise BridgeError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                "Media Monitor could not inspect the video",
            ) from None
        self._log_result(path=INSPECT_PATH, status=HTTPStatus.OK, code="ok", video_id=video_id)
        return payload

    def _summary(self, video_id: str) -> dict:
        item_uid = f"youtube:{video_id}"
        with self._mutation_lock:
            if self.store.load_item(item_uid) is None:
                raise BridgeError(
                    HTTPStatus.NOT_FOUND,
                    "video_not_found",
                    "Video is not present in governed Media Monitor state",
                )
            current = build_sidecar(self.store, video_id)
            summary_state = current["summary"]
            if summary_state["state"] == "available":
                self._log_result(
                    path=SUMMARY_PATH,
                    status=HTTPStatus.OK,
                    code="cached_summary",
                    video_id=video_id,
                )
                return current
            if summary_state["state"] != "not_attempted" and summary_state["retryable"] is False:
                self._log_result(
                    path=SUMMARY_PATH,
                    status=HTTPStatus.OK,
                    code=f"cached_{summary_state['state']}",
                    video_id=video_id,
                )
                return current

            provider = self.summary_provider_factory()
            if provider is None:
                raise BridgeError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "summary_provider_unconfigured",
                    "Summary provider is unavailable",
                )

            try:
                payload = ensure_video_sidecar(
                    self.store,
                    video_id,
                    metadata_client=None,
                    summary_provider=provider,
                )
            except Exception as exc:
                # ensure_video_sidecar returns the governed sidecar for the current
                # provider_limit/failed states. Reaching here means no safe state was
                # materialized and the exception must stay server-side.
                self._log_exception(SUMMARY_PATH, "summary_provider_error", exc)
                raise BridgeError(
                    HTTPStatus.BAD_GATEWAY,
                    "summary_provider_error",
                    "Summary provider failed",
                ) from None

        self._log_result(
            path=SUMMARY_PATH,
            status=HTTPStatus.OK,
            code=str(payload["summary"]["state"]),
            video_id=video_id,
        )
        return payload

    @staticmethod
    def _log_result(*, path: str, status: int, code: str, video_id: str | None = None) -> None:
        LOGGER.info(
            json.dumps(
                {
                    "event": "youtube_sidecar_http_result",
                    "path": path,
                    "status": int(status),
                    "code": code,
                    "video_id": video_id,
                },
                sort_keys=True,
            )
        )

    @staticmethod
    def _log_exception(path: str, code: str, exc: Exception) -> None:
        # Deliberately omit exception text: upstream bodies, keys and local paths
        # must not cross the bridge's structured-log boundary.
        LOGGER.warning(
            json.dumps(
                {
                    "event": "youtube_sidecar_http_failure",
                    "path": path,
                    "code": code,
                    "error_class": type(exc).__name__,
                },
                sort_keys=True,
            )
        )


def _json_response(handler: BaseHTTPRequestHandler, response: BridgeResponse) -> None:
    data = json.dumps(response.payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    handler.send_response(int(response.status))
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(data)


def _read_json_body(handler: BaseHTTPRequestHandler) -> object:
    if handler.headers.get("Transfer-Encoding"):
        raise BridgeError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "Transfer-Encoding is not supported",
        )
    raw_length = handler.headers.get("Content-Length")
    try:
        length = int(raw_length or "")
    except ValueError:
        raise BridgeError(
            HTTPStatus.LENGTH_REQUIRED,
            "content_length_required",
            "A valid Content-Length header is required",
        ) from None
    if length < 1:
        raise BridgeError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "Request body is required",
        )
    if length > MAX_REQUEST_BYTES:
        raise BridgeError(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "request_too_large",
            "Request body is too large",
        )
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BridgeError(
            HTTPStatus.BAD_REQUEST,
            "invalid_json",
            "Request body must be valid JSON",
        ) from None


def make_server(
    *,
    bridge: YouTubeSidecarBridge,
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                _json_response(self, BridgeResponse(HTTPStatus.OK, {"status": "ok"}))
                return
            _json_response(
                self,
                BridgeError(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found").response(),
            )

        def do_POST(self) -> None:
            try:
                payload = _read_json_body(self)
            except BridgeError as exc:
                _json_response(self, exc.response())
                return
            _json_response(self, bridge.post(self.path, payload))

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer((host, port), Handler)


def serve(*, store_root: Path, host: str, port: int) -> None:
    bridge = YouTubeSidecarBridge(MediaWatchStore(store_root))
    make_server(bridge=bridge, host=host, port=port).serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the private governed YouTube sidecar HTTP bridge")
    parser.add_argument("--store-root", type=Path, default=None)
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    serve(
        store_root=args.store_root or _configured_store_root(),
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
