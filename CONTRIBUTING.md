# Contributing to Media Monitor

Media Monitor accepts small, bounded changes that preserve explicit authority and ownership boundaries.

## Start here

```bash
python -m pip install -r requirements-sensing.txt pytest jsonschema requests
bin/media demo
python -m pytest -q tests/test_adopter_demo.py tests/test_example_outlet.py
```

For Next.js changes:

```bash
npm --prefix apps/news_site ci
npm --prefix apps/news_site run typecheck
```

## Choose one contribution lane

### Contracts and deterministic read models

Typical scope: `contracts/`, deterministic builders, validators and tests.

Required invariants:

- schemas are versioned;
- deterministic outputs have stable IDs/provenance;
- monitored/selected/generated/published states remain distinct;
- no outlet-specific condition is slipped into a reusable builder without a platform-level reason.

### Acquisition and enrichment

Typical scope: `apps/news_acquire/`, `apps/news_enrich/` and their owned tests.

Do not make the frontend reach into these owners directly. Cross-owner integration goes through declared buses/indexes/contracts.

### Editorial generation

Typical scope: `apps/news_editorial/`.

Generating a brief or draft does not confer publication authority. Never bypass the explicit promotion gate.

### Public outlet

Typical scope: `apps/news_site/` plus compiled snapshot/identity contracts.

The frontend renders compiled public truth. It must not invent upstream facts, approvals or freshness.

### Adopter/reuse surface

Typical scope: `examples/`, README/tutorials and configuration surfaces.

A second outlet should not require editing generic compiler logic. If it does, describe the missing reusable primitive explicitly.

## Publication authority

The critical invariant is:

```text
monitored ≠ selected ≠ generated ≠ approved ≠ published
```

Only a valid `published_article.v1` that crossed the explicit human publication gate is eligible for the public editorial layer.

Toy/rehearsal fixtures may exercise `human_approved` consumer paths only when isolated and explicitly marked as not for publication.

## Pull request shape

Prefer one coherent contract/owner change per PR. A good PR normally contains:

1. a narrow mission;
2. explicit non-goals;
3. production invariant(s) being protected;
4. tests that would fail if the boundary regressed;
5. copied commands/results or CI evidence;
6. truthful notes about anything not empirically verified.

Do not weaken an ownership or publication guard merely to make a mixed PR pass. Split the packet instead.

## Before opening a PR

Run the smallest relevant checks first, then broader CI:

```bash
bin/media demo
python -m pytest -q <relevant tests>
```

When touching the public outlet:

```bash
npm --prefix apps/news_site run typecheck
```

The repository's `Runtime contracts` workflow is the merge gate for runtime semantics. The docs-site workflow separately protects docs/deployment ownership isolation.

## Evidence and screenshots

Do not attach a screenshot as proof of freshness or publication status when a machine-readable health/contract artifact is available.

For visual changes, screenshots are welcome when they are captured from the actual changed surface. Never fabricate a screenshot from fixture/demo data and present it as production.

See [`EVIDENCE.md`](EVIDENCE.md) for the current evidence map.

## Security and secrets

Never commit local `.env*`, Vercel tokens, credentials, private source material or unreviewed sensitive data. Production identities and external-provider actions must remain auditable and explicit.

## Need a bounded first task?

See [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md). Each item is intentionally small enough to review independently.
