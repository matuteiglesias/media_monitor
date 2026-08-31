import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "contracts" / "schemas"
FIXTURES_DIR = ROOT / "contracts" / "tests" / "fixtures"


CASES = [
    ("news_ref.v1.json", "news_ref.example.json"),
    ("scrape_request.v1.json", "scrape_request.example.json"),
    ("scraped_article.v1.json", "scraped_article.example.json"),
    ("news_digest_group.v1.json", "news_digest_group.example.json"),
    ("news_topic_cluster.v1.json", "news_topic_cluster.example.json"),
    ("news_seed_idea.v1.json", "news_seed_idea.example.json"),
    ("news_seed_card.v1.json", "news_seed_card.example.json"),
    ("news_piece_brief.v1.json", "news_piece_brief.example.json"),
    ("news_article_draft.v1.json", "news_article_draft.example.json"),
    ("news_yt_script_draft.v1.json", "news_yt_script_draft.example.json"),
    ("published_article.v1.json", "published_article.example.json"),
    ("publication_health.v1.json", "publication_health.example.json"),
    ("editorial_selection.v1.json", "editorial_selection.example.json"),
    ("story_context.v1.json", "story_context.example.json"),
    ("site_snapshot.v2.json", "site_snapshot.v2.example.json"),
    ("site_snapshot.v3.json", "site_snapshot.v3.example.json"),
    ("site_snapshot.v4.json", "site_snapshot.v4.example.json"),
    ("media_watch_spec.v1.json", "media_watch_spec.example.json"),
    ("media_source.v1.json", "media_source.a.example.json"),
    ("media_source.v1.json", "media_source.b.example.json"),
    ("media_item.v1.json", "media_item.example.json"),
    ("media_metadata_snapshot.v1.json", "media_metadata_snapshot.example.json"),
    ("media_text_asset.v1.json", "media_text_asset.unavailable.example.json"),
    ("media_text_asset.v1.json", "media_text_asset.publisher.example.json"),
    ("media_segment.v1.json", "media_segment.example.json"),
    ("media_appearance.v1.json", "media_appearance.example.json"),
]


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_contract_fixtures_validate_against_schemas():
    for schema_name, fixture_name in CASES:
        schema = _load_json(SCHEMAS_DIR / schema_name)
        fixture = _load_json(FIXTURES_DIR / fixture_name)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(fixture), key=lambda e: e.path)
        assert not errors, f"{fixture_name} failed {schema_name}: {[e.message for e in errors]}"


def test_monitored_media_w0_proves_two_sources_and_two_people_by_configuration():
    watch = _load_json(FIXTURES_DIR / "media_watch_spec.example.json")
    sources = [
        _load_json(FIXTURES_DIR / "media_source.a.example.json"),
        _load_json(FIXTURES_DIR / "media_source.b.example.json"),
    ]

    assert set(watch["source_ids"]) == {source["source_id"] for source in sources}
    assert len(watch["source_ids"]) == 2
    assert len({person["person_id"] for person in watch["people"]}) == 2
    assert all(source["discovery"]["method"] == "channel_uploads_playlist" for source in sources)


def test_monitored_media_item_identity_is_separate_from_mutable_snapshot():
    item = _load_json(FIXTURES_DIR / "media_item.example.json")
    snapshot = _load_json(FIXTURES_DIR / "media_metadata_snapshot.example.json")

    assert item["item_uid"] == f"youtube:{item['native_id']}"
    assert snapshot["item_uid"] == item["item_uid"]
    assert snapshot["snapshot_id"] != item["item_uid"]


def test_monitored_media_text_absence_is_valid_and_available_text_is_hash_bound():
    unavailable = _load_json(FIXTURES_DIR / "media_text_asset.unavailable.example.json")
    publisher = _load_json(FIXTURES_DIR / "media_text_asset.publisher.example.json")

    assert unavailable["status"] == "unavailable"
    assert unavailable["text"] is None
    assert unavailable["text_sha256"] is None

    assert publisher["status"] == "publisher_transcript"
    assert publisher["text"]
    assert hashlib.sha256(publisher["text"].encode("utf-8")).hexdigest() == publisher["text_sha256"]


def test_monitored_media_segment_and_appearance_link_without_redefining_item():
    item = _load_json(FIXTURES_DIR / "media_item.example.json")
    segment = _load_json(FIXTURES_DIR / "media_segment.example.json")
    appearance = _load_json(FIXTURES_DIR / "media_appearance.example.json")

    assert segment["item_uid"] == item["item_uid"]
    assert 0 <= segment["start_seconds"] < segment["end_seconds"] <= item["duration_seconds"]
    assert appearance["item_uid"] == item["item_uid"]
    assert appearance["segment_id"] == segment["segment_id"]
    assert appearance["evidence_source"] == "title"
