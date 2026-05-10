"""Scraped article record models emitted by news_enrich."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

FetchStatus = Literal["success", "failed", "blocked", "empty", "timeout"]


class ScrapedArticle(BaseModel):
    """Schema-valid scraped_article.v1 enrichment artifact."""

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["scraped_article.v1"] = "scraped_article.v1"
    schema_status: Literal["experimental"] = "experimental"
    index_id: str = Field(..., min_length=1)
    source_url: HttpUrl
    final_url: HttpUrl | None = None
    fetched_at: datetime
    fetch_status: FetchStatus
    title: str = ""
    source: str = ""
    topic: str = ""
    text: str = ""
    text_hash: str = ""
    byte_size: int = Field(default=0, ge=0)
    char_count: int = Field(default=0, ge=0)
    language: str | None = None
    error_code: str = ""
    error_message: str = ""
    extractor: str = "requests_basic"
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("index_id", "title", "source", "topic", "text", "text_hash", "error_code", "error_message", "extractor", mode="before")
    @classmethod
    def _strip_strings(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @property
    def ok(self) -> bool:
        return self.fetch_status == "success"
