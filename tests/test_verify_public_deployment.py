from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_public_deployment import main, resolve_public_url, validate_health


def roll_record():
    return {
        "status": "ok",
        "site_id": "argentina-general",
        "digest_at": "20260824T18",
        "snapshot_id": "a" * 64,
        "deployment_host": "roll-abc.vercel.app",
        "expected": {
            "item_count": 11,
            "section_count": 3,
            "published_article_count": 2,
            "curated_signal_count": 6,
            "story_context_count": 11,
        },
    }


def public_health(**publication_overrides):
    publication = {
        "schema_name": "publication_health.v1",
        "freshness_status": "FRESH",
        "is_current": True,
        "within_target": True,
        "age_minutes": 25,
    }
    publication.update(publication_overrides)
    return {
        "status": "ok",
        "site_id": "argentina-general",
        "digest_at": "20260824T18",
        "snapshot_id": "a" * 64,
        "item_count": 11,
        "section_count": 3,
        "published_article_count": 2,
        "curated_signal_count": 6,
        "story_context_count": 11,
        "publication_health": publication,
    }


def test_public_health_must_match_roll_and_freshness_target():
    report = validate_health(roll_record(), public_health())
    assert report["status"] == "ok"
    assert report["freshness_status"] == "FRESH"
    assert report["within_target"] is True
    assert report["published_article_count"] == 2
    assert report["curated_signal_count"] == 6
    assert report["story_context_count"] == 11


def test_public_identity_mismatch_fails():
    bad = public_health()
    bad["snapshot_id"] = "b" * 64
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_health(roll_record(), bad)


def test_publication_count_identity_mismatch_fails():
    bad = public_health()
    bad["published_article_count"] = 1
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_health(roll_record(), bad)


def test_curated_count_identity_mismatch_fails():
    bad = public_health()
    bad["curated_signal_count"] = 5
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_health(roll_record(), bad)


def test_story_context_count_identity_mismatch_fails():
    bad = public_health()
    bad["story_context_count"] = 10
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_health(roll_record(), bad)


def test_public_stale_state_fails():
    with pytest.raises(ValueError, match="not fresh"):
        validate_health(
            roll_record(),
            public_health(
                freshness_status="STALE",
                is_current=False,
                within_target=False,
                age_minutes=500,
            ),
        )


def test_public_target_miss_fails_even_if_still_fresh():
    with pytest.raises(ValueError, match="missed target"):
        validate_health(roll_record(), public_health(within_target=False, age_minutes=150))


def test_public_url_uses_provider_url_until_owned_domain_is_active():
    identity = {
        "public_outlet_url": "https://provider.example/",
        "owned_outlet_url": "https://owned.example",
    }
    assert resolve_public_url(identity, False) == "https://provider.example"
    assert resolve_public_url(identity, True) == "https://owned.example"


@pytest.mark.parametrize(
    "public_url",
    ["", "http://provider.example", "https://provider.example/unexpected-path"],
)
def test_public_url_must_be_an_https_origin(public_url):
    with pytest.raises(ValueError, match="invalid public_outlet_url"):
        resolve_public_url({"public_outlet_url": public_url}, False)


def test_main_fetches_configured_public_url(tmp_path, monkeypatch):
    roll_path = tmp_path / "roll.json"
    identity_path = tmp_path / "identity.json"
    output_path = tmp_path / "report.json"
    roll_path.write_text(json.dumps(roll_record()), encoding="utf-8")
    identity_path.write_text(
        json.dumps(
            {
                "public_outlet_url": "https://provider.example",
                "owned_outlet_url": "https://owned.example",
            }
        ),
        encoding="utf-8",
    )
    requested = []
    monkeypatch.setattr(
        "verify_public_deployment.fetch_health",
        lambda public_url, timeout: requested.append((public_url, timeout)) or public_health(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_public_deployment.py",
            "--roll-record",
            str(roll_path),
            "--public-identity",
            str(identity_path),
            "--output",
            str(output_path),
        ],
    )

    assert main() == 0
    assert requested == [("https://provider.example", 20.0)]
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["deployment_host"] == "roll-abc.vercel.app"
    assert report["public_url"] == "https://provider.example"
