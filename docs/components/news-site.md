# news_site

> **Status:** canonical component guide · **Verified against:** `7723918`

`apps/news_site` owns rendering a generated, validated public snapshot with Next.js routes for home, latest, story, topic, and health. It does not own editorial facts, approval, internal indexes, content ingestion, or provider deployment state.

| Interface | Input | Output/consumer |
|---|---|---|
| snapshot refresh/build | validated storage indexes/published indexes | `apps/news_site/public/data/*` |
| generic site compiler | site config + coherent news indexes | schema-valid `site_snapshot.v1` |
| Next build | public data snapshot | prebuilt deploy artifact |
| health route | built snapshot | identity/count reconciliation for roll tooling |

**Invariants:** public data is an allowlisted projection; required inputs fail loudly; fallback is opt-in for local preview; snapshot ID is deterministic over content; deployment does not mutate source truth. Current `publish_news_site.sh` expects npm scripts absent from `package.json`, so that aggregate route is not end-to-end runnable.

**Dependencies:** Node/Next.js, Python snapshot builders/validators, site config, and deployment CLI only for a roll. **Tests:** refresh-data, snapshot validator, build-site-snapshot, validate-site-snapshot, and site-roll suites.

See [trust boundaries](../architecture/trust-boundaries.md) and [buses/indexes/storage](../reference/buses-indexes-and-storage.md).
