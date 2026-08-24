from scripts.publish_last_mile_snapshot import build_public_snapshot


def test_public_snapshot_preserves_editorial_priority_and_draft_headline():
    source = {
        "digest_at": "20260824T12",
        "built_at": "20260824T150000Z",
        "status": "ok",
        "metrics": {
            "seed_ideas_emitted": 2,
            "briefs_emitted": 1,
            "drafts_emitted": 1,
            "fallback_legacy_count": 0,
            "schema_failures": 0,
        },
        "human_handoff": {
            "status": "ready",
            "action_candidates": [
                {
                    "priority": "high",
                    "target_format": "article",
                    "title": "A ranked candidate",
                }
            ],
            "latest_article_drafts": [
                {
                    "headline": "A bus-backed draft",
                    "draft_id": "draft-123",
                }
            ],
            "latest_yt_script_drafts": [],
        },
    }

    public = build_public_snapshot(source)

    assert public["human_handoff"]["action_candidates"] == [
        {
            "priority": "high",
            "kind": "article",
            "title": "A ranked candidate",
        }
    ]
    assert public["human_handoff"]["latest_article_drafts"] == [
        {
            "title": "A bus-backed draft",
            "index_id": "draft-123",
        }
    ]


def test_public_snapshot_keeps_allowlist_and_safe_fallbacks():
    source = {
        "digest_at": "20260824T12",
        "built_at": "20260824T150000Z",
        "status": "ok",
        "secret": "must-not-leak",
        "metrics": {},
        "human_handoff": {
            "status": "ready",
            "action_candidates": [{}],
            "latest_article_drafts": [{}],
            "latest_yt_script_drafts": [],
            "private_pointer": "/tmp/internal",
        },
    }

    public = build_public_snapshot(source)

    assert "secret" not in public
    assert "private_pointer" not in public["human_handoff"]
    assert public["human_handoff"]["action_candidates"][0]["priority"] == "normal"
    assert public["human_handoff"]["latest_article_drafts"][0]["title"] == "sin título"
