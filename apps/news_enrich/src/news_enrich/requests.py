"""Request models for on-demand article enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EnrichRequest(BaseModel):
    """Small, source-agnostic request consumed by the enrich service.

    The same request shape can be built from a queue payload, a news_ref.v1 row,
    an editorial handoff, or a manual CLI invocation.
    """

    model_config = ConfigDict(extra="forbid")

    index_id: str = Field(..., min_length=1, description="Stable article/reference id.")
    url: HttpUrl = Field(..., description="Article URL to fetch.")
    title: str = ""
    source: str = ""
    topic: str = ""
    digest_at: str | None = None
    priority: Literal["high", "normal", "low"] = "normal"
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("index_id", "title", "source", "topic", "digest_at", mode="before")
    @classmethod
    def _strip_optional_strings(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @classmethod
    def from_queue_payload(cls, index_id: str, payload: dict[str, Any] | None) -> "EnrichRequest":
        """Build an EnrichRequest from existing scrape queue payload conventions."""
        payload = payload or {}
        url = payload.get("url") or payload.get("link") or payload.get("original_link")
        return cls(
            index_id=payload.get("index_id") or index_id,
            url=url,
            title=payload.get("title", ""),
            source=payload.get("source", ""),
            topic=payload.get("topic", ""),
            digest_at=payload.get("digest_at") or payload.get("digest_id_hour"),
            priority=payload.get("priority", "normal"),
            metadata={k: v for k, v in payload.items() if k not in {"index_id", "url", "link", "original_link", "title", "source", "topic", "digest_at", "digest_id_hour", "priority"}},
        )
