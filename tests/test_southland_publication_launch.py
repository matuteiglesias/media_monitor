from __future__ import annotations

import json
from pathlib import Path

import scripts.promote_draft_to_published as promote_module
from scripts.deploy_outlet import deployment_env
from scripts.materialize_outlet_site import materialize


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture_repo(root: Path) -> None:
    write_json(root / "config/policy.json", {"policy_id": "fixture"})
    write_json(
        root / "config/public.json",
        {
            "schema_name": "public_identity.v1",
            "outlet_name": "Southland",
            "outlet_tagline": "Ficción",
            "public_outlet_url": "https://southland.invalid",
            "owned_outlet_url": "https://southland.invalid",
            "owned_domain_status": "unconfigured",
            "legacy_outlet_urls": [],
            "docs_url": "https://example.test/docs",
            "repository_url": "https://example.test/repo",
            "owner_url": "https://example.test/owner",
        },
    )
    write_json(
        root / "config/editorial.json",
        {
            "schema_name": "editorial_identity.v1",
            "outlet_name": "Southland",
            "endorsement_line": "Ficción satírica",
            "editor": {
                "name": "Editor",
                "role": "Editor",
                "bio_short": "Bio",
                "location": "Buenos Aires",
                "credentials": ["A"],
                "expertise": ["B"],
                "contact": {
                    "email": "editor@example.test",
                    "website": "https://example.test",
                    "linkedin": "https://example.test/linkedin",
                    "github": "https://example.test/github",
                },
                "same_as": ["https://example.test", "https://example.test/about"],
            },
            "routes": {
                "about": "/about",
                "methodology": "/methodology",
                "journalists": "/journalists",
                "author": "/authors/editor",
            },
        },
    )
    write_json(
        root / "sites/southland.json",
        {
            "site_id": "southland",
            "name": "Southland",
            "tagline": "Ficción",
            "locale": "es-AR",
            "runtime": {
                "data_dir": ".runtime/southland/data",
                "storage_dir": ".runtime/southland/storage",
                "selection_policy": "config/policy.json",
            },
            "build": {
                "public_identity": "config/public.json",
                "editorial_identity": "config/editorial.json",
            },
            "deployment": {
                "provider": "vercel",
                "org_id_env": "ORG_SOURCE",
                "project_id_env": "PROJECT_SOURCE",
                "public_url_env": "PUBLIC_SOURCE",
            },
            "selection": {
                "topics": ["All Topics"],
                "max_age_hours": 3,
                "minimum_items": 1,
                "max_items": 10,
            },
            "presentation": {
                "latest_count": 10,
                "show_sources": True,
                "mode": "publication",
                "theme": "southland",
                "publication_label": "Ficción satírica · aprobación humana",
            },
        },
    )
    write_json(
        root / ".runtime/southland/storage/public/site_snapshot.json",
        {"schema_name": "site_snapshot.v4", "site": {"site_id": "southland"}, "digest_at": "20260918T21"},
    )


def test_materializer_projects_outlet_identity_presentation_and_snapshot(tmp_path, monkeypatch) -> None:
    fixture_repo(tmp_path)
    monkeypatch.setenv("PUBLIC_SOURCE", "https://southland.example.test")

    result = materialize(repo_root=tmp_path, site_id="southland")

    assert result["presentation_mode"] == "publication"
    assert result["public_outlet_url"] == "https://southland.example.test"
    public = json.loads((tmp_path / "apps/news_site/config/public_identity.json").read_text())
    presentation = json.loads((tmp_path / "apps/news_site/config/site_presentation.json").read_text())
    snapshot = json.loads((tmp_path / "apps/news_site/public/data/site_snapshot.json").read_text())
    assert public["outlet_name"] == "Southland"
    assert public["public_outlet_url"] == "https://southland.example.test"
    assert presentation["mode"] == "publication"
    assert snapshot["site"]["site_id"] == "southland"


def test_deployment_env_maps_outlet_specific_project_without_mutating_source_names(monkeypatch) -> None:
    site = {
        "deployment": {
            "provider": "vercel",
            "org_id_env": "ORG_SOURCE",
            "project_id_env": "SOUTHLAND_PROJECT",
        }
    }
    env = deployment_env(site, base={"ORG_SOURCE": "org-1", "SOUTHLAND_PROJECT": "project-2"})
    assert env["VERCEL_ORG_ID"] == "org-1"
    assert env["VERCEL_PROJECT_ID"] == "project-2"


def test_promotion_can_target_configured_southland_runtime(tmp_path, monkeypatch) -> None:
    fixture_repo(tmp_path)
    draft = {
        "schema_name": "news_article_draft.v1",
        "draft_id": "southland-draft-1",
        "digest_at": "20260918T21",
        "story_group_id": "southland::1",
        "title": "Southland title",
        "slug_candidate": "southland-title",
        "summary": "Summary",
        "body_md": "Body",
        "topic": "Política",
        "source_links": ["https://example.test/source"],
        "citations": [],
        "status": "draft",
    }
    draft_path = tmp_path / ".runtime/southland/storage/buses/news_article_draft/v1/southland-draft-1.jsonl"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(json.dumps(draft) + "\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "promote_draft_to_published.py",
            "--repo-root", str(tmp_path),
            "--site-id", "southland",
            "--draft-id", "southland-draft-1",
            "--approve-human",
        ],
    )

    assert promote_module.main() == 0
    published = list((tmp_path / ".runtime/southland/storage/buses/published_article/v1").glob("*.jsonl"))
    assert len(published) == 1
    assert json.loads(published[0].read_text())["review_status"] == "human_approved"


def test_southland_reader_surface_and_two_step_human_release_are_explicit() -> None:
    home = (ROOT / "apps/news_site/components/SouthlandHome.tsx").read_text()
    article = (ROOT / "apps/news_site/app/articles/[slug]/page.tsx").read_text()
    prepare = (ROOT / ".github/workflows/southland-prepare.yml").read_text()
    publish = (ROOT / ".github/workflows/southland-publish.yml").read_text()
    site = json.loads((ROOT / "sites/southland.json").read_text())

    assert site["presentation"]["mode"] == "publication"
    assert "Fuentes reales, ficción marcada" in home
    assert "Qué es real y qué no" in article
    assert "run_outlet_ai.py" in prepare
    assert "upload-artifact@v4" in prepare
    assert "draft_ids" in publish
    assert "PUBLISH SOUTHLAND" in publish
    assert "--approve-human" in publish
    assert "SOUTHLAND_VERCEL_PROJECT_ID" in publish
    assert "deploy_outlet.py" in publish
