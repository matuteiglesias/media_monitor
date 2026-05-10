import sys
import types

sys.modules.setdefault("psycopg", types.SimpleNamespace(connect=lambda *args, **kwargs: None))

from apps.news_editorial.src.news_editorial import stage05_explode_pf_outputs as stage05
from apps.news_editorial.src.news_editorial import stage06_build_piece_briefs as stage06


def test_stage06_extract_seed_ideas_normalizes_legacy_key() -> None:
    row = {
        "seed_ideas": {
            "seed_ideas": [
                {
                    "idea_id": "A1",
                    "idea_title": "Título",
                    "key_data_points": ["dato legacy"],
                }
            ]
        }
    }

    ideas = stage06.extract_seed_ideas(row)

    assert len(ideas) == 1
    assert ideas[0]["key_facts"] == ["dato legacy"]


def test_stage05_builds_draft_from_brief_as_canonical_input() -> None:
    brief = {
        "schema_name": "news_piece_brief.v1",
        "brief_id": "npb_123",
        "digest_id_hour": "20260101T01",
        "digest_file": "hour_20260101T0100",
        "topic": "Economía",
        "working_title": "Titular desde brief",
        "angle": "Ángulo desde brief",
        "source_index_ids": ["IDX001"],
    }
    mapped_by_index = {
        "IDX001": {
            "index_id": "IDX001",
            "article_id": "10",
            "digest_file": "hour_20260101T0100",
            "Title": "Título mapeado",
            "Source": "Fuente",
            "Link": "https://example.com/a",
            "Published": "2026-01-01T01:00:00Z",
            "Topic": "Economía",
        }
    }

    draft, err = stage05.make_draft_obj_from_brief(brief, mapped_by_index)

    assert err is None
    assert draft is not None
    assert draft["headline"] == "Titular desde brief"
    assert draft["dek"] == "Ángulo desde brief"
    assert draft["cluster_id"] == "npb_123"
    assert draft["meta"]["brief_schema"] == "news_piece_brief.v1"
    assert draft["citations"][0]["url"] == "https://example.com/a"


def test_stage06_brief_id_is_stable_by_digest_group_and_idea() -> None:
    idea = {"idea_id": "EC01"}
    one = stage06._brief_id("20260101T01", "20260101T01::hour::eco::01", idea, 1)
    two = stage06._brief_id("20260101T01", "20260101T01::hour::eco::01", idea, 99)

    assert one == two
    assert one.startswith("npb_")


def test_draft_bus_writer_promotes_stage05_draft_to_schema_valid_buses(tmp_path) -> None:
    from apps.news_editorial.src.news_editorial.draft_bus_writer import (
        article_draft_from_stage05,
        validate_article_draft,
        validate_yt_script_draft,
        write_article_draft,
        write_yt_script_draft,
        yt_script_draft_from_stage05,
    )

    stage05_draft = {
        "digest_id_hour": "20260101T01",
        "index_id": "IDX001",
        "topic": "Economía",
        "headline": "Titular desde brief",
        "dek": "Ángulo desde brief",
        "citations": [{"url": "https://example.com/a", "title": "Fuente", "source": "Example"}],
        "cluster_id": "npb_123",
        "meta": {"brief_id": "npb_123"},
    }

    article = article_draft_from_stage05(stage05_draft)
    yt_script = yt_script_draft_from_stage05(stage05_draft)

    validate_article_draft(article)
    validate_yt_script_draft(yt_script)
    article_path = write_article_draft(article, bus_dir=tmp_path / "news_article_draft" / "v1")
    yt_path = write_yt_script_draft(yt_script, bus_dir=tmp_path / "news_yt_script_draft" / "v1")

    assert article_path.exists()
    assert yt_path.exists()
    assert article_path.read_text(encoding="utf-8").count("\n") == 1
    assert yt_path.read_text(encoding="utf-8").count("\n") == 1


def test_stage05_writes_draft_buses_before_optional_mirror(tmp_path, monkeypatch) -> None:
    import importlib
    import json

    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    digest_id = "20260314T17"

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("DIGEST_AT", digest_id)
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.setenv("WRITE_DRAFT_MIRROR", "0")

    digest_map = data_dir / "digest_map" / f"{digest_id}.csv"
    digest_map.parent.mkdir(parents=True, exist_ok=True)
    digest_map.write_text(
        "digest_file,article_id,index_id,Title,Source,Link,Published,Topic\n"
        "A_20260314T1700,1,IDX001,Título mapeado,Fuente,https://example.com/a,2026-03-14T17:10:00Z,Economía\n",
        encoding="utf-8",
    )
    pf_out = data_dir / "pf_out" / f"pfout_{digest_id}.jsonl"
    pf_out.parent.mkdir(parents=True, exist_ok=True)
    pf_out.write_text(
        json.dumps({"digest_group_id": f"{digest_id}::A::Economia::01", "seed_ideas": {"seed_ideas": []}}) + "\n",
        encoding="utf-8",
    )
    brief_bus = storage_dir / "buses" / "news_piece_brief" / "v1" / "npb_123.jsonl"
    brief_bus.parent.mkdir(parents=True, exist_ok=True)
    brief_bus.write_text(
        json.dumps(
            {
                "schema_name": "news_piece_brief.v1",
                "brief_id": "npb_123",
                "digest_id_hour": digest_id,
                "digest_file": "A_20260314T1700",
                "topic": "Economía",
                "working_title": "Titular desde brief",
                "angle": "Ángulo desde brief",
                "source_index_ids": ["IDX001"],
                "format_candidates": ["both"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    mod = importlib.reload(stage05)
    monkeypatch.setattr(mod.db, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(mod.db, "finish_run", lambda *a, **k: None)

    assert mod.run() == 0

    article_files = list((storage_dir / "buses" / "news_article_draft" / "v1").glob("*.jsonl"))
    yt_files = list((storage_dir / "buses" / "news_yt_script_draft" / "v1").glob("*.jsonl"))
    assert len(article_files) == 1
    assert len(yt_files) == 1
    assert not (data_dir / "drafts" / digest_id).exists()
    assert json.loads(article_files[0].read_text(encoding="utf-8"))["schema_name"] == "news_article_draft.v1"
    assert json.loads(yt_files[0].read_text(encoding="utf-8"))["schema_name"] == "news_yt_script_draft.v1"
