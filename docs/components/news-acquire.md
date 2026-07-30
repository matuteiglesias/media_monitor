# news_acquire

> **Status:** canonical component guide · **Verified against:** `7723918`

`apps.news_acquire` owns feed configuration/loading, stages 01–03, stable sensed-news identity, and isolated sensing-run production. It does not own enrichment, editorial approval, publication, or the compactor's canonical pointer.

| Interface | Input | Output/consumer |
|---|---|---|
| stages 01–03 | `DIGEST_AT`, feed config, prior local state | Level-0 RSS slices, digest map, grouped JSONL |
| export seam | Level-0 acquire outputs | `news_ref.v1`, `news_digest_group.v1`, `scrape_request.v1` buses |
| sensing bundle | digest/run controls and isolated roots | immutable manifest/checksums/candidates for compactor |
| S3 producer | finalized bundle | unique immutable run prefix; `FINALIZED` last |

**Invariants:** UTC hour identity; normalized stable `index_id`; schema-valid exports; no overwrite of finalized bundles; producer cannot update generations/current. Failures stop later stages and remain evidence/quarantine. Missing/invalid finalization or checksum makes a bundle ineligible.

**Dependencies:** pandas/feedparser, optional PostgreSQL bookkeeping, public feed network, JSON schemas; AWS mode additionally uses boto3 and task environment. **Tests:** sensing characterization, run-bundle, compactor, S3, container-task, Terraform-packet, export, and news-index suites.

**Extension rule:** add acquisition behavior inside the owner module and cross the boundary through a versioned bus or immutable bundle. Do not add a new compatibility wrapper as the owner. See [contracts](../reference/contracts-and-schemas.md), [configuration](../reference/configuration.md), and [architecture](../architecture/lane-and-owner-boundaries.md).
