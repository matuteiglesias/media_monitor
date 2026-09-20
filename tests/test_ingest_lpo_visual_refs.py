from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

from scripts.ingest_lpo_visual_refs import (
    asset_family_key,
    collect_urls_from_rss,
    discover_images,
    ingest,
    parse_srcset,
)


ARTICLE_URL = "https://www.lapoliticaonline.com/politica/nota-prueba/"
HERO_URL = "https://cdn.example.test/photos/hero-1600.jpg"
INLINE_URL = "https://cdn.example.test/photos/inline-1200.webp"


def jpeg_bytes(width: int = 1200, height: int = 675) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        text: str = "",
        content: bytes = b"",
        status_code: int = 200,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.url = url
        self.text = text
        self.content = content or text.encode("utf-8")
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def get(self, url: str, **_kwargs):
        self.calls.append(url)
        return self.responses[url]

    def close(self) -> None:
        pass


def fixture_html() -> str:
    return f"""
    <html>
      <head>
        <link rel="canonical" href="{ARTICLE_URL}">
        <meta property="og:title" content="Una prueba visual de LPO">
        <meta property="og:image" content="{HERO_URL}">
        <meta property="article:published_time" content="2026-09-19T12:00:00-03:00">
        <meta property="article:section" content="Política">
        <script type="application/ld+json">
        {{
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": "Una prueba visual de LPO",
          "datePublished": "2026-09-19T12:00:00-03:00",
          "articleSection": "Política",
          "image": "{HERO_URL}"
        }}
        </script>
      </head>
      <body>
        <header><img src="https://www.lapoliticaonline.com/logo.png" alt="logo"></header>
        <article>
          <h1>Una prueba visual de LPO</h1>
          <figure>
            <img
              src="https://cdn.example.test/photos/hero-640.jpg"
              srcset="https://cdn.example.test/photos/hero-640.jpg 640w, {HERO_URL} 1600w"
              alt="Dos dirigentes durante una reunión"
            >
            <figcaption>Dos dirigentes reunidos. Foto: Agencia Prueba</figcaption>
          </figure>
          <p>Texto de la noticia.</p>
          <figure>
            <img src="{INLINE_URL}" alt="Una segunda escena">
            <figcaption>Segunda escena de la reunión.</figcaption>
          </figure>
        </article>
      </body>
    </html>
    """


def test_lpo_asset_family_collapses_generated_crop_variant() -> None:
    original = "https://www.lapoliticaonline.com/files/image/289/289253/6a1f2281e9429.jpg"
    crop = "https://www.lapoliticaonline.com/files/image/289/289253/6a1f2281e9429_1200_630!.jpg?s=abc&d=123"
    assert asset_family_key(original) == asset_family_key(crop)


def test_parse_srcset_prefers_largest_candidate() -> None:
    assert parse_srcset(
        "https://example.test/640.jpg 640w, https://example.test/1600.jpg 1600w",
        ARTICLE_URL,
    ) == "https://example.test/1600.jpg"


def test_discover_images_extracts_article_metadata_credit_and_skips_logo() -> None:
    metadata, images = discover_images(fixture_html(), ARTICLE_URL, ARTICLE_URL)

    assert metadata["canonical_url"] == ARTICLE_URL
    assert metadata["headline"] == "Una prueba visual de LPO"
    assert metadata["section"] == "Política"
    assert metadata["published_at"] == "2026-09-19T12:00:00-03:00"
    assert [row.url for row in images] == [HERO_URL, INLINE_URL]
    assert images[0].role == "hero"
    assert images[0].credit == "Foto: Agencia Prueba"
    assert images[0].alt_text == "Dos dirigentes durante una reunión"
    assert all("logo" not in row.url for row in images)


def test_lpo_vsmsrc_gallery_enriches_same_asset_with_alt_and_credit() -> None:
    html = """
    <html><head>
      <meta property="og:image" content="https://www.lapoliticaonline.com/files/image/1/2/abc123.jpg">
    </head><body>
      <div class="media">
        <script>
          var x=null;vsm.load.check('window.vplfgal',{arguments:['gallery1',[
            {"i":"/files/image/1/2/abc123_940_529!.jpg?s=token","w":"1544","h":"1032","id":"2","t":"Escena principal","a":"Agencia Demo","mq":[]}
          ],2,'','',false,'',],variable:'x'});
        </script>
        <div class="gallery">
          <div class="g_controls"><div class="image"><picture>
            <img src="data:image/png;base64,AAA" vsmsrc="/files/image/1/2/abc123_940_529!.jpg?s=token" alt="Una escena política">
          </picture></div></div>
          <div class="media-footer"><div class="caption"></div><div class="g_source_author"><span class="author g_author"></span></div></div>
        </div>
      </div>
    </body></html>
    """
    _meta, images = discover_images(
        html,
        ARTICLE_URL,
        "https://www.lapoliticaonline.com/politica/nota-prueba/",
    )

    assert len(images) == 1
    assert images[0].url == "https://www.lapoliticaonline.com/files/image/1/2/abc123.jpg"
    assert images[0].role == "hero"
    assert images[0].caption == "Escena principal"
    assert images[0].credit == "Agencia Demo"
    assert images[0].alt_text == "Una escena política"


def test_lpo_gallery_config_captures_multiple_images() -> None:
    html = """
    <html><body>
      <div class="media">
        <script>
          vsm.load.check('window.vplfgal',{arguments:['gallery1',[
            {"i":"/files/image/1/2/a.jpg","w":"1200","h":"800","id":"a","t":"Uno","a":"Agencia Uno","mq":[]},
            {"i":"/files/image/1/2/b.jpg","w":"1200","h":"800","id":"b","t":"Dos","a":"Agencia Dos","mq":[]}
          ],2,'','',false,'',],variable:'x'});
        </script>
        <div class="gallery">
          <img src="data:image/png;base64,AAA" vsmsrc="/files/image/1/2/a.jpg" alt="Primera">
        </div>
      </div>
    </body></html>
    """
    _meta, images = discover_images(html, ARTICLE_URL, ARTICLE_URL)

    assert [row.role for row in images] == ["hero", "inline"]
    assert [row.caption for row in images] == ["Uno", "Dos"]
    assert [row.credit for row in images] == ["Agencia Uno", "Agencia Dos"]


def test_ingest_downloads_manifests_and_is_idempotent(tmp_path: Path) -> None:
    hero = jpeg_bytes()
    inline = jpeg_bytes(900, 600)
    session = FakeSession(
        {
            ARTICLE_URL: FakeResponse(url=ARTICLE_URL, text=fixture_html()),
            HERO_URL: FakeResponse(
                url=HERO_URL,
                content=hero,
                content_type="image/jpeg",
            ),
            INLINE_URL: FakeResponse(
                url=INLINE_URL,
                content=inline,
                content_type="image/webp",
            ),
        }
    )
    output = tmp_path / "visuals/references"

    first = ingest(
        urls=[ARTICLE_URL],
        output_root=output,
        session=session,
        now="2026-09-20T00:00:00Z",
    )
    calls_after_first = len(session.calls)
    second = ingest(
        urls=[ARTICLE_URL],
        output_root=output,
        session=session,
        now="2026-09-20T00:05:00Z",
    )

    articles = [
        json.loads(line)
        for line in (output / "manifests/lpo_articles.jsonl").read_text().splitlines()
    ]
    images = [
        json.loads(line)
        for line in (output / "manifests/lpo_images.jsonl").read_text().splitlines()
    ]
    originals = list((output / "originals").glob("*"))

    assert first["status"] == "ok"
    assert first["succeeded_article_count"] == 1
    assert first["unique_image_manifest_count"] == 2
    assert first["downloaded_file_count"] == 2
    assert len(articles) == 1
    assert len(images) == 2
    assert len(originals) == 2
    assert {row["rights_status"] for row in images} == {"reference_only"}
    assert {row["publish_original"] for row in images} == {False}
    assert {row["download_status"] for row in images} == {"ok"}
    assert {row["width"] for row in images} == {1200, 900}
    assert len(session.calls) == calls_after_first
    assert second["processed_article_count"] == 0
    assert second["reused_count"] == 1


def test_ingest_records_article_failure_without_aborting_batch(tmp_path: Path) -> None:
    bad = "https://www.lapoliticaonline.com/politica/falla/"
    session = FakeSession(
        {
            bad: FakeResponse(url=bad, status_code=404),
            ARTICLE_URL: FakeResponse(url=ARTICLE_URL, text=fixture_html()),
            HERO_URL: FakeResponse(url=HERO_URL, content=jpeg_bytes(), content_type="image/jpeg"),
            INLINE_URL: FakeResponse(url=INLINE_URL, content=jpeg_bytes(900, 600), content_type="image/webp"),
        }
    )

    report = ingest(
        urls=[bad, ARTICLE_URL],
        output_root=tmp_path / "visuals/references",
        session=session,
        now="2026-09-20T00:00:00Z",
    )

    assert report["status"] == "partial"
    assert report["processed_article_count"] == 2
    assert report["succeeded_article_count"] == 1
    assert report["failed_article_count"] == 1


def test_collect_urls_from_rss_dedupes_cross_listed_articles(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "feeds.yaml"
    config.write_text(
        """schema_version: sensing_feeds.v1
feeds:
  - topic: Política
    url: https://example.test/politica.xml
  - topic: Economía
    url: https://example.test/economia.xml
""",
        encoding="utf-8",
    )

    class Entry:
        def __init__(self, link: str, published_parsed=None) -> None:
            self.link = link
            self.published_parsed = published_parsed

    newer = (2026, 9, 19, 15, 0, 0, 5, 262, 0)
    older = (2026, 9, 19, 14, 0, 0, 5, 262, 0)

    def parse(url: str):
        if "politica" in url:
            return type("Feed", (), {"entries": [Entry(ARTICLE_URL, newer), Entry("https://example.test/not-lpo", newer)]})()
        return type("Feed", (), {"entries": [Entry(ARTICLE_URL, newer), Entry("https://www.lapoliticaonline.com/economia/otra/", older)]})()

    monkeypatch.setattr("scripts.ingest_lpo_visual_refs.feedparser.parse", parse)

    assert collect_urls_from_rss(config, limit=10) == [
        ARTICLE_URL,
        "https://www.lapoliticaonline.com/economia/otra/",
    ]
