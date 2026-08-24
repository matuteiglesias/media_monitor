from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "news_site"
sys.path.insert(0, str(ROOT / "scripts"))

from verify_owned_domain_readiness import verify


def test_identity_declares_owned_target_without_premature_cutover():
    identity = json.loads((SITE / "config" / "public_identity.json").read_text(encoding="utf-8"))
    runtime = (SITE / "lib" / "public_identity.ts").read_text(encoding="utf-8")
    middleware = (SITE / "middleware.ts").read_text(encoding="utf-8")

    assert identity["public_outlet_url"] == "https://mediamonitor-psi.vercel.app"
    assert identity["owned_outlet_url"] == "https://media.matuteiglesias.link"
    assert identity["owned_domain_status"] == "pending_dns_activation"
    assert identity["public_outlet_url"] in identity["legacy_outlet_urls"]
    assert 'process.env.CANONICAL_OWNED_DOMAIN_ACTIVE === "1"' in runtime
    assert "identity.owned_outlet_url" in runtime
    assert 'process.env.CANONICAL_OWNED_DOMAIN_ACTIVE !== "1"' in middleware
    assert "NextResponse.redirect(target, 308)" in middleware


def test_scheduled_roll_owns_activation_flag_and_readiness_is_manual():
    scheduled = (ROOT / ".github" / "workflows" / "scheduled-publication.yml").read_text(encoding="utf-8")
    readiness = (ROOT / ".github" / "workflows" / "owned-domain-readiness.yml").read_text(encoding="utf-8")
    runbook = (ROOT / "OWNED_DOMAIN_CUTOVER.md").read_text(encoding="utf-8")

    assert "CANONICAL_OWNED_DOMAIN_ACTIVE" in scheduled
    assert "owned_outlet_url" in scheduled
    assert "workflow_dispatch" in readiness
    assert "verify_owned_domain_readiness.py" in readiness
    assert "CHECK media.matuteiglesias.link" in readiness
    assert "CANONICAL_OWNED_DOMAIN_ACTIVE=1" in runbook
    assert "CANONICAL_OWNED_DOMAIN_ACTIVE=0" in runbook
    assert "Do **not** change `public_outlet_url` manually" in runbook


def test_readiness_requires_dns_https_and_snapshot_parity():
    health = {
        "status": "ok",
        "site_id": "argentina-general",
        "snapshot_id": "a" * 64,
        "canonical_url": "https://mediamonitor-psi.vercel.app",
    }
    report = verify(
        "https://media.matuteiglesias.link",
        "https://mediamonitor-psi.vercel.app",
        resolver=lambda host: ["203.0.113.10"],
        fetcher=lambda url: dict(health),
    )
    assert report["status"] == "ready"
    assert report["snapshot_id"] == "a" * 64

    def mismatched(url: str):
        value = dict(health)
        if "mediamonitor-psi" in url:
            value["snapshot_id"] = "b" * 64
        return value

    try:
        verify(
            "https://media.matuteiglesias.link",
            "https://mediamonitor-psi.vercel.app",
            resolver=lambda host: ["203.0.113.10"],
            fetcher=mismatched,
        )
    except ValueError as exc:
        assert "same snapshot" in str(exc)
    else:
        assert False
