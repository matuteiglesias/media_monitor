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
