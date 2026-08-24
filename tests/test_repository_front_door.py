from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_contributor_contract_preserves_authority_and_has_runnable_entrypoints() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "bin/media demo" in text
    assert "published_article.v1" in text
    assert "monitored ≠ selected ≠ generated ≠ approved ≠ published" in text
    assert "Never bypass" not in text  # avoid imperative ambiguity; exact gate language lives below
    assert "Never bypass the explicit promotion gate" in text
    assert "Do not weaken an ownership or publication guard" in text
    assert "EVIDENCE.md" in text


def test_issue_and_pr_templates_route_changes_to_bounded_boundaries() -> None:
    pr = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    bug = (ROOT / ".github/ISSUE_TEMPLATE/bug.yml").read_text(encoding="utf-8")
    reuse = (ROOT / ".github/ISSUE_TEMPLATE/reuse_request.yml").read_text(encoding="utf-8")
    assert "Invariants protected" in pr
    assert "no publication gate bypass" in pr
    assert "Primary boundary" in bug
    assert "Smallest reusable primitive" in reuse
    assert "examples/outlet/" in reuse


def test_evidence_ledger_does_not_substitute_fake_screenshots_for_production() -> None:
    evidence = (ROOT / "EVIDENCE.md").read_text(encoding="utf-8")
    assert "https://mediamonitor-psi.vercel.app/api/health" in evidence
    assert "freshness_status=FRESH" in evidence
    assert "does not check in a fabricated or stale homepage screenshot" in evidence
    assert "toy acceptance" in evidence.lower()
    assert "bin/media demo" in evidence


def test_good_first_tasks_are_bounded_and_not_core_rewrite_prompts() -> None:
    text = (ROOT / "GOOD_FIRST_ISSUES.md").read_text(encoding="utf-8")
    assert text.count("## ") >= 5
    assert text.count("**DoD:**") >= 5
    assert "no demo semantics change" in text
    assert "core generic builders unchanged" in text


def test_linguist_hygiene_only_marks_truthful_non_core_surfaces() -> None:
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "artifacts/** linguist-generated=true" in attrs
    assert "*.md linguist-documentation=true" in attrs
    for forbidden in ("apps/**", "scripts/**", "*.py", "*.ts", "*.tsx"):
        assert forbidden not in attrs
