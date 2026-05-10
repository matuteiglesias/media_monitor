from pydantic import BaseModel, Field, HttpUrl, AwareDatetime, field_validator
from typing import List, Optional, Literal, Dict

Lang = Literal["es", "en"]


class ScrapedData(BaseModel):
    final_url: Optional[HttpUrl] = None
    text: Optional[str] = None           # normalized text/plain (optional; can be large)
    text_hash: Optional[str] = None      # sha256 of normalized text
    byte_size: Optional[int] = None
    fetched_at: Optional[str] = None     # ISO-8601 UTC


class ScrapeRecordV1(BaseModel):
    schema_version: Literal["ScrapeRecordV1"] = "ScrapeRecordV1"
    index_id: str = Field(min_length=10, max_length=10)
    digest_id_hour: str = Field(min_length=11, max_length=11)  # YYYYMMDDTHH
    topic: str
    source: str
    title: str
    published: AwareDatetime
    original_link: HttpUrl
    final_url: HttpUrl
    redirects: List[str] = []
    status: int
    fetch_latency_ms: int
    raw_html_len: int
    main_text: str
    main_text_len: int
    lang: Optional[Lang] = None
    canonical_url: Optional[HttpUrl] = None
    byline: Optional[str] = None
    lead_image_url: Optional[HttpUrl] = None
    extraction_engine: Literal["trafilatura", "readability", "playwright"]
    quality: Dict[str, float] = {}
    fetched_at: AwareDatetime

    @field_validator("digest_id_hour")
    @classmethod
    def _check_did(cls, v: str) -> str:
        # Very light format check
        assert len(v) == 11 and v[8] == "T", "digest_id_hour must be YYYYMMDDTHH"
        return v

    scraped_data: Optional[ScrapedData] = None

    @field_validator("title", "source", "original_link", mode="before", check_fields=False)
    @classmethod
    def _strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

    def validate_minimal(self) -> Optional[str]:
        if not (self.title and self.source and self.original_link):
            return "missing: title/source/original_link"
        if self.published is None:
            return "missing: published"
        return None


class CitationV1(BaseModel):
    title: str
    source: str
    url: HttpUrl
    published: Optional[AwareDatetime] = None


class ArticleDraftV1(BaseModel):
    schema_version: Literal["ArticleDraftV1"] = "ArticleDraftV1"
    cluster_id: str
    slug: str
    lang: Lang
    headline: str
    dek: Optional[str] = None
    body_html: str
    bullet_summary: List[str] = []
    citations: List[CitationV1]
    topic: str
    tags: List[str] = []
    seo: Dict[str, str] = {}              # meta_title, meta_description
    created_at: AwareDatetime
    flow_version: str                     # prompt/provenance
    first_seen_at: AwareDatetime


class ArticleV1(BaseModel):
    schema_version: Literal["ArticleV1"] = "ArticleV1"
    article_id: str
    slug: str
    lang: Lang
    headline: str
    dek: Optional[str] = None
    body_html: str
    topic: str
    tags: List[str]
    citations: List[CitationV1]
    related_ids: List[str] = []
    published_at: AwareDatetime           # site publish time
    first_seen_at: AwareDatetime          # earliest member
    cluster_id: str
    version: int = 1
    meta: Dict[str, str] = {}
