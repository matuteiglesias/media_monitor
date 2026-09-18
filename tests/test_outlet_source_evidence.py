from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from apps.news_acquire.src.news_acquire import stage01_digests as stage01
from apps.news_enrich.src.news_enrich.service import FetchResult, extract_text
from scripts.build_editorial_selection import build as build_selection
from scripts.enrich_selected_signals import enrich_selected
from scripts.outlet_runtime import resolve_outlet_runtime
from scripts.refresh_outlet_evidence import Result, run_sensing


ROOT = Path(__file__).resolve().parents[1]
DIGEST = "20260918T21"
NOW = "2026-09-18T21:30:00Z"
NOW_DT = datetime(2026, 9, 18, 21, 30, tzinfo=timezone.utc)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def fixture_site(root: Path) -> None:
    write_json(
        root / "config/policy.json",
        {
            "policy_id": "fixture-v1",
            "policy_version": "1",
            "max_age_minutes": 180,
            "future_tolerance_minutes": 5,
            "minimum_items": 1,
            "max_items": 10,
            "high_priority_threshold": 8,
            "default_topic_weight": 4,
            "topic_weights": {},
            "freshness_buckets": [
                {"max_age_minutes": 180, "score": 10, "reason_code": "fresh_under_180m"}
            ],
            "first_source_bonus": 0,
            "first_topic_bonus": 0,
            "repeat_source_penalty": 0,
            "repeat_topic_penalty": 0,
        },
    )
    (root / "config/feeds.yaml").parent.mkdir(parents=True, exist_ok=True)
    (root / "config/feeds.yaml").write_text(
        "schema_version: sensing_feeds.v1\nfeeds:\n  - topic: Política\n    url: https://example.test/rss\n",
        encoding="utf-8",
    )
    write_json(
        root / "sites/southland.json",
        {
            "site_id": "southland",
            "name": "Southland",
            "tagline": "fixture",
            "locale": "es-AR",
            "runtime": {
                "data_dir": ".runtime/southland/data",
                "storage_dir": ".runtime/southland/storage",
                "selection_policy": "config/policy.json",
                "feed_config": "config/feeds.yaml",
                "source_name": "La Política Online",
            },
            "selection": {
                "topics": ["All Topics"],
                "max_age_hours": 3,
                "minimum_items": 1,
                "max_items": 20,
            },
            "presentation": {"latest_count": 12, "show_sources": True},
        },
    )


def test_southland_uses_official_lpo_section_feeds_and_three_hour_frontier() -> None:
    site = json.loads((ROOT / "sites/southland.json").read_text(encoding="utf-8"))
    feeds = yaml.safe_load(
        (ROOT / "config/sensing_feeds.southland.yaml").read_text(encoding="utf-8")
    )
    topics = [row["topic"] for row in feeds["feeds"]]

    assert site["runtime"]["feed_config"] == "config/sensing_feeds.southland.yaml"
    assert site["runtime"]["source_name"] == "La Política Online"
    assert site["runtime"]["storage_dir"] == ".runtime/southland/storage"
    assert site["selection"]["max_age_hours"] == 3
    assert topics == [
        "Política",
        "Economía",
        "Ciudad",
        "Provincia",
        "Conurbano",
        "Santa Fe",
        "Judiciales",
        "Campo",
        "Medios",
    ]
    assert all(
        row["url"].startswith("http://www.lapoliticaonline.com.ar/files/rss/")
        for row in feeds["feeds"]
    )


def test_configured_publisher_identity_overrides_rss_source(monkeypatch) -> None:
    monkeypatch.setenv("SENSING_SOURCE_NAME", "La Política Online")
    monkeypatch.setattr(
        stage01.feedparser,
        "parse",
        lambda _url: SimpleNamespace(
            entries=[
                SimpleNamespace(
                    title="Una noticia",
                    link="https://www.lapoliticaonline.com/politica/una-noticia/",
                    published="Fri, 18 Sep 2026 18:15:00 -0300",
                    source=SimpleNamespace(title="Unexpected embedded label"),
                )
            ]
        ),
    )

    frame = stage01.fetch_rss_now({"Política": "https://example.test/rss"}, limit=None)

    assert len(frame) == 1
    assert frame.iloc[0]["Source"] == "La Política Online"
    assert frame.iloc[0]["Topic"] == "Política"


def test_sensing_pipeline_routes_every_mutable_path_to_outlet_runtime(tmp_path: Path) -> None:
    fixture_site(tmp_path)
    runtime = resolve_outlet_runtime(tmp_path, "southland")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def runner(command, *, cwd, env):
        assert cwd == tmp_path.resolve()
        calls.append((list(command), dict(env)))
        return Result(list(command), 0, "ok", "")

    stages = run_sensing(
        runtime=runtime,
        digest_at=DIGEST,
        runner=runner,
        python_executable="python-test",
        limit=25,
    )

    assert [row["stage"] for row in stages] == [
        "s01",
        "s02",
        "s03",
        "export_pr3a",
        "build_news_access_indexes",
    ]
    assert len(calls) == 5
    for _, env in calls:
        assert env["DATA_DIR"] == str(tmp_path / ".runtime/southland/data")
        assert env["STORAGE_DIR"] == str(tmp_path / ".runtime/southland/storage")
        assert env["SENSING_FEED_CONFIG"] == str(tmp_path / "config/feeds.yaml")
        assert env["SENSING_SOURCE_NAME"] == "La Política Online"
        assert env["ENQUEUE_SCRAPE"] == "0"
        assert env["DB_RUN_BOOKKEEPING"] == "0"
        assert env["LIMIT"] == "25"

    export_command = calls[3][0]
    assert str(tmp_path / ".runtime/southland/data") in export_command
    assert str(tmp_path / ".runtime/southland/storage") in export_command
    assert "data" not in export_command
    assert "storage" not in export_command


def test_southland_selector_is_deterministic_bounded_and_topic_diverse(tmp_path: Path) -> None:
    topics = ["Política", "Política", "Política", "Economía", "Economía", "Provincia", "Ciudad", "Conurbano", "Santa Fe", "Judiciales", "Campo", "Medios"]
    refs = []
    for idx, topic in enumerate(topics):
        refs.append(
            {
                "digest_at": DIGEST,
                "index_id": f"id-{idx:02d}",
                "title": f"Historia {idx:02d}",
                "topic": topic,
                "published_at": f"2026-09-18T{21 - (idx % 2):02d}:{20 - (idx % 10):02d}:00Z",
                "link": f"https://www.lapoliticaonline.com/{idx}/",
                "source": "La Política Online",
            }
        )
    refs_path = tmp_path / "refs.jsonl"
    write_jsonl(refs_path, refs)

    one = build_selection(
        refs_path=refs_path,
        policy_path=ROOT / "config/editorial_selection.southland.json",
        digest_at=DIGEST,
        as_of=NOW,
        output=tmp_path / "one.json",
    )
    two = build_selection(
        refs_path=refs_path,
        policy_path=ROOT / "config/editorial_selection.southland.json",
        digest_at=DIGEST,
        as_of=NOW,
        output=tmp_path / "two.json",
    )

    assert one["selection_id"] == two["selection_id"]
    assert one["metrics"]["selected_count"] == 10
    assert len({row["topic"] for row in one["selected"]}) >= 6
    assert all(row["score_components"]["repeat_source_penalty"] == 0 for row in one["selected"])


def _article_html(marker: str) -> str:
    body = " ".join([f"{marker} evidencia verificable del cuerpo de la nota."] * 40)
    return (
        "<html><body>"
        "<nav>NAVEGACION QUE NO DEBE ENTRAR</nav>"
        f"<article><h1>{marker}</h1><p>{body}</p><aside>RELACIONADAS</aside></article>"
        "<footer>PIE QUE NO DEBE ENTRAR</footer>"
        "</body></html>"
    )


def test_selected_enrichment_yields_clean_evidence_and_replay_dedupes(tmp_path: Path) -> None:
    fixture_site(tmp_path)
    storage = tmp_path / ".runtime/southland/storage"
    selected = []
    topics = ["Política", "Economía", "Provincia", "Ciudad", "Conurbano", "Santa Fe"]
    for idx, topic in enumerate(topics, start=1):
        selected.append(
            {
                "rank": idx,
                "index_id": f"lpo-{idx}",
                "title": f"Nota LPO {idx}",
                "topic": topic,
                "published_at": "2026-09-18T21:10:00Z",
                "link": f"https://www.lapoliticaonline.com/{topic.lower()}/nota-{idx}/",
                "source": "La Política Online",
                "score": 50 - idx,
                "score_components": {
                    "topic_priority": 10,
                    "freshness": 30,
                    "first_source_bonus": 0,
                    "first_topic_bonus": 4,
                    "repeat_source_penalty": 0,
                    "repeat_topic_penalty": 0,
                },
                "reason_codes": ["fresh_under_60m", "high_topic_priority", "repeat_source_penalty", "new_topic_bonus"],
            }
        )
    write_json(
        storage / "indexes/editorial_selection_latest.json",
        {
            "schema_name": "editorial_selection.v1",
            "selection_id": "a" * 64,
            "digest_at": DIGEST,
            "selected": selected,
        },
    )

    def fetcher(url: str) -> FetchResult:
        marker = url.rstrip("/").split("/")[-1]
        html = _article_html(marker)
        return FetchResult(
            status_code=200,
            final_url=url,
            html=html,
            byte_size=len(html.encode("utf-8")),
            fetched_at=NOW_DT,
        )

    first = enrich_selected(
        repo_root=tmp_path,
        site_id="southland",
        digest_at=DIGEST,
        max_items=6,
        minimum_successes=5,
        minimum_text_chars=500,
        timeout=5,
        now=NOW_DT,
        fetcher=fetcher,
    )
    second = enrich_selected(
        repo_root=tmp_path,
        site_id="southland",
        digest_at=DIGEST,
        max_items=6,
        minimum_successes=5,
        minimum_text_chars=500,
        timeout=5,
        now=NOW_DT,
        fetcher=fetcher,
    )

    bus_files = sorted((storage / "buses/scraped_article/v1").glob("*.jsonl"))
    rows = [
        json.loads(line)
        for path in bus_files
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert first["status"] == "ok"
    assert first["accepted_success_count"] == 6
    assert first["written_count"] == 6
    assert second["status"] == "ok"
    assert second["accepted_success_count"] == 6
    assert second["written_count"] == 0
    assert second["skipped_unchanged_count"] == 6
    assert len(rows) == 6
    assert {row["source"] for row in rows} == {"La Política Online"}
    assert {row["extractor"] for row in rows} == {"html_article"}
    assert all(row["char_count"] >= 500 for row in rows)
    assert all("NAVEGACION QUE NO DEBE ENTRAR" not in row["text"] for row in rows)
    assert all("PIE QUE NO DEBE ENTRAR" not in row["text"] for row in rows)
    assert (storage / "indexes/enrich_latest.json").is_file()


def test_jsonld_article_body_is_preferred_over_page_chrome() -> None:
    body = "Texto de la nota " * 80
    document = (
        "<html><head>"
        '<script type="application/ld+json">'
        + json.dumps({"@type": "NewsArticle", "articleBody": body})
        + "</script></head><body><nav>MENU</nav><main>OTRO CONTENIDO</main></body></html>"
    )

    text, extractor = extract_text(document)

    assert extractor == "jsonld_article"
    assert text.startswith("Texto de la nota")
    assert "MENU" not in text
    assert "OTRO CONTENIDO" not in text
