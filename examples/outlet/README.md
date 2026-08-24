# Build another outlet

This folder is the canonical adopter example for Media Monitor.

It proves a second outlet can compile through the same generic selection, context and `site_snapshot.v4` machinery without editing `apps/**` or the core Python builders.

## Run it

From the repository root:

```bash
python examples/outlet/build.py
```

Output:

```text
.demo/example-outlet/site_snapshot.json
.demo/example-outlet/build_manifest.json
```

The example is deterministic fixture data. It is not live news and contains no public editorial approval.

## The five things an adopter changes

### 1. Outlet identity and presentation

Edit `example-general.json`:

- `site_id`
- `name`
- `tagline`
- `locale`
- `selection.topics`
- `presentation.latest_count`

For a real Next deployment, also provide deployment-specific public/editor identity configuration equivalent to `apps/news_site/config/public_identity.json` and `editorial_identity.json`. Those are configuration surfaces, not Python compiler changes.

### 2. Topics and source acquisition

Replace the fixture signals with your own acquisition layer that emits the stable monitored-signal/access-index fields:

```text
index_id
digest_at
title
topic
published_at
link
source
```

The Argentina deployment uses `apps/news_acquire`; another adopter can use a different acquisition implementation as long as it materializes the same boundary.

### 3. Deterministic selection policy

Edit `editorial_selection.example.json`:

- topic weights
- freshness buckets
- diversity bonuses
- repeat penalties
- minimum/maximum shortlist size

The generic `scripts/build_editorial_selection.py` does not know about Argentina topic names.

### 4. Presentation/read-model limits

Use the site config to choose allowed topics, age limits and visible counts. The generic `build_site_snapshot.py` reads those values rather than hard-coding the Argentina deployment.

### 5. Deployment

Choose your own host/domain and deployment project. Keep deployment identity separate from provider URLs, and apply the same health/canonical/redirect discipline used by Media Monitor.

## What should not change

A new outlet should not need edits to:

- `scripts/build_editorial_selection.py`
- `scripts/build_story_contexts.py`
- `scripts/build_site_snapshot.py`
- `contracts/schemas/editorial_selection.v1.json`
- `contracts/schemas/story_context.v1.json`
- `contracts/schemas/site_snapshot.v4.json`

If a real adopter discovers a legitimate need to modify those files, treat it as a reusable-platform requirement rather than slipping an outlet-specific condition into core code.

## Example layout

```text
examples/outlet/
├── README.md
├── build.py
├── example-general.json
├── editorial_selection.example.json
└── fixtures/
    ├── signals.json
    └── groups.json
```

The fixture-to-snapshot path is:

```text
signals
  ↓
editorial_selection.v1
  ↓
story_context.v1
  ↓
site_snapshot.v4
```

This example deliberately stops before live acquisition and production deployment: those are adapter/operator concerns around the reusable compiler boundary.
