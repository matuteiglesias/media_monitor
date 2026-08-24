from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_public_deployment import validate_health


def roll_record():
    return {
        "status": "ok",
        "site_id": "argentina-general",
        "digest_at": "20260824T18",
        "snapshot_id": "a" * 64,
        "deployment_host": "roll-abc.vercel.app",
        "expected": {"item_count": 11, "section_count": 3},
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
        "publication_health": publication,
    }


def test_public_health_must_match_roll_and_freshness_target():
    report = validate_health(roll_record(), public_health())
    assert report["status"] == "ok"
    assert report["freshness_status"] == "FRESH"
    assert report["within_target"] is True


def test_public_identity_mismatch_fails():
    bad = public_health()
    bad["snapshot_id"] = "b" * 64
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
        validate_health(
            roll_record(), public_health(within_target=False, age_minutes=150)
        )
