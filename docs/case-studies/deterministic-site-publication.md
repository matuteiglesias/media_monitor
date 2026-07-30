# Deterministic site and publication snapshots

> **Status:** evidence-based case study · **Verified against:** `ec3765a` · **Maturity:** implemented and locally validated; provider operation unverified

## Problem and constraints

A public site must not read raw PromptFlow output, quarantine, credentials, or mutable internal workspace. A successful build also cannot prove that the intended digest/content reached a deployment. The design had to preserve human approval, source provenance, deterministic identity, static deployment, and a small failure surface without creating a parallel CMS.

## Before and after

**Before:** public routes could depend on copied “latest” JSON with freshness/fallback ambiguity, and deployment success was weakly coupled to content identity.

**After:** contract buses and compact indexes remain internal truth; explicit human promotion creates `published_article.v1`; index builders derive public read models; snapshot builders validate coherent digest/config/source rows, project allowlisted fields, record source hashes/Git SHA, and atomically replace output. `snapshot_id` hashes canonical content while excluding operational `generated_at`. Site-roll tooling prebuilds and requires `/api/health` to return the exact snapshot identity and counts.

## Authority and trust

Editorial generation cannot publish. The promotion command refuses without explicit human approval and retains draft/story/digest/citation provenance. Snapshot builders may project but not mutate buses or approval. The browser consumes `public/data`, never internal paths or provider secrets. Vercel is deployment transport, not editorial authority.

## Failure, replay, and rollback

Missing/empty/invalid inputs, mixed digest, stale selection, schema failure, fallback, build failure, or health mismatch stops publication. Identical canonical input yields the same snapshot ID; source changes yield a new identity. Rollback selects a prior known-good deployment and verifies its health identity rather than hand-editing public JSON. Approval evidence is not deleted as rollback.

## Alternatives rejected

A second CMS, browser reads from raw buses/workspace, silent editorial fallback, timestamp-only snapshot IDs, deployment exit as proof, and content fixes directly in public JSON were rejected because they split authority or destroy provenance.

## Evidence and current gap

Source and tests cover human-gated promotion/validation seams, published indexes, publish-surface validation, snapshot schema and deterministic ID, input freshness/digest checks, atomic writes, prebuild orchestration, and health reconciliation. However, `scripts/publish_news_site.sh` currently calls npm scripts absent from `apps/news_site/package.json`, so that aggregate route is denied. Repository evidence does not establish a live or repeatedly operated Vercel deployment. See the [human last-mile](../operations/editorial-human-last-mile.md) and [site/Vercel runbook](../operations/site-snapshot-and-vercel.md).
