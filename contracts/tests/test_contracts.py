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
