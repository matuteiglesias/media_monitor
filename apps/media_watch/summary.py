from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .enrichment import MediaEnrichmentStore
from .store import MediaWatchStore, utc_now

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
PROMPT_VERSION = "youtube-summary.v1"
PROVIDER_NAME = "google-gemini"
ADAPTER_VERSION = "gemini-youtube-url.v1"
PROCESSING_MODE = "static"

SUMMARY_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "key_points": {
            "type": "array",
            "minItems": 1,
            "maxItems": 12,
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": ["summary", "key_points"],
}

SUMMARY_PROMPT = """Summarize this video for a reader deciding whether it deserves further attention.

Use the video's natural language.

Preserve the substantive content rather than the presentation style. Include:
- the central subject or question;
- the main arguments, claims, findings, or events;
- important names, dates, numbers, and concrete facts;
- meaningful disagreements, uncertainty, or qualifications;
- the conclusion or takeaway when there is one.

Produce a self-contained summary that makes sense without watching the video. Aim for roughly 300-700 useful words when the content warrants it rather than padding to a fixed length. Also return roughly 3-8 concise key points.

Do not invent information unsupported by the video. Do not add generic commentary or recommendations.
"""


def _validate_response(payload: object) -> dict:
    errors = sorted(
        Draft202012Validator(SUMMARY_RESPONSE_SCHEMA).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError(
            "Gemini summary response validation failed: "
            + "; ".join(error.message for error in errors[:5])
        )
    assert isinstance(payload, dict)
    return payload


def _exception_status_code(exc: Exception) -> int | None:
    for value in (
        getattr(exc, "status_code", None),
        getattr(exc, "code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def classify_summary_failure(exc: Exception) -> tuple[str, bool]:
    message = str(exc).casefold()
    provider_limit_markers = (
        "maximum number of tokens",
        "token limit",
        "input token limit",
        "context window",
        "1048576",
    )
    if any(marker in message for marker in provider_limit_markers):
        return "provider_limit", False

    # Invalid structured output is a deterministic model/contract failure for
    # this exact attempt.  Retrying it blindly is not the transient-recovery
    # policy exercised by the sidecar.
    if isinstance(exc, ValueError):
        return "failed", False

    status = _exception_status_code(exc)
    if status in {408, 429, 500, 502, 503, 504}:
        return "failed", True
    if status is not None and 400 <= status < 500:
        return "failed", False

    nonretryable_markers = (
        "permission denied",
        "forbidden",
        "unauthorized",
        "invalid argument",
        "invalid_argument",
        "policy block",
        "safety block",
    )
    if any(marker in message for marker in nonretryable_markers):
        return "failed", False

    # Preserve the existing conservative retryable default for opaque upstream
    # availability/network failures that do not expose a structured status.
    return "failed", True


class GeminiSummaryProvider:
    """Thin adapter over Gemini's native public YouTube URL understanding."""

    provider_name = PROVIDER_NAME

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        adapter_version: str = ADAPTER_VERSION,
        processing_mode: str = PROCESSING_MODE,
        client: Any | None = None,
    ) -> None:
        if not api_key.strip() and client is None:
            raise ValueError("GEMINI_API_KEY is required")
        self.api_key = api_key.strip()
        self.model = model.strip() or DEFAULT_GEMINI_MODEL
        self.adapter_version = adapter_version.strip() or ADAPTER_VERSION
        self.processing_mode = processing_mode.strip() or PROCESSING_MODE
        self._client = client

    def _client_or_create(self) -> Any:
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError(
                    "google-genai is required for live YouTube summary generation; "
                    "install requirements-media-watch-ai.txt"
                ) from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def summarize_youtube(self, url: str) -> dict:
        interaction = self._client_or_create().interactions.create(
            model=self.model,
            input=[
                {"type": "text", "text": SUMMARY_PROMPT},
                {"type": "video", "uri": url},
            ],
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": SUMMARY_RESPONSE_SCHEMA,
            },
            store=False,
        )
        output_text = getattr(interaction, "output_text", None)
        if not output_text:
            raise RuntimeError("Gemini returned no summary text")
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini returned invalid JSON for media summary") from exc
        return _validate_response(payload)


def ensure_summary(
    store: MediaWatchStore,
    *,
    item_uid: str,
    provider: GeminiSummaryProvider,
    generated_at: str | None = None,
) -> tuple[dict, str]:
    """Return the versioned summary artifact and whether it was generated or reused."""

    item = store.load_item(item_uid)
    if item is None:
        raise ValueError(f"unknown item {item_uid}")

    enrichment = MediaEnrichmentStore(store)
    existing = enrichment.load_summary(
        item_uid=item_uid,
        provider=provider.provider_name,
        model=provider.model,
        prompt_version=PROMPT_VERSION,
        adapter_version=provider.adapter_version,
        processing_mode=provider.processing_mode,
    )
    if existing is not None:
        return existing, "existing"

    attempted_at = generated_at or utc_now()
    try:
        result = provider.summarize_youtube(item["canonical_url"])
    except Exception as exc:
        state, retryable = classify_summary_failure(exc)
        enrichment.put_summary_attempt(
            item_uid=item_uid,
            provider=provider.provider_name,
            model=provider.model,
            prompt_version=PROMPT_VERSION,
            adapter_version=provider.adapter_version,
            processing_mode=provider.processing_mode,
            attempted_at=attempted_at,
            state=state,
            retryable=retryable,
            error_class=type(exc).__name__,
            error_message=" ".join(str(exc).split())[:1000] or type(exc).__name__,
        )
        raise

    artifact = enrichment.put_summary(
        item_uid=item_uid,
        summary=result["summary"],
        key_points=result["key_points"],
        provider=provider.provider_name,
        model=provider.model,
        prompt_version=PROMPT_VERSION,
        adapter_version=provider.adapter_version,
        processing_mode=provider.processing_mode,
        generated_at=attempted_at,
    )
    enrichment.put_summary_attempt(
        item_uid=item_uid,
        provider=provider.provider_name,
        model=provider.model,
        prompt_version=PROMPT_VERSION,
        adapter_version=provider.adapter_version,
        processing_mode=provider.processing_mode,
        attempted_at=attempted_at,
        state="generated",
        retryable=False,
    )
    return artifact, "generated"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or reuse a governed Gemini summary for an existing YouTube media item"
    )
    parser.add_argument("item_uid", help="Canonical media item UID (youtube:<video-id>) or native YouTube video ID")
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--model", default=None, help="Gemini model; defaults to GEMINI_MODEL or gemini-3.8-flash")
    args = parser.parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        parser.error("GEMINI_API_KEY is required")

    model = (args.model or os.environ.get("GEMINI_MODEL", "") or DEFAULT_GEMINI_MODEL).strip()
    item_uid = args.item_uid if args.item_uid.startswith("youtube:") else f"youtube:{args.item_uid}"
    provider = GeminiSummaryProvider(api_key=api_key, model=model)
    artifact, state = ensure_summary(
        MediaWatchStore(args.store_root),
        item_uid=item_uid,
        provider=provider,
    )
    print(json.dumps({"state": state, "summary": artifact}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
