# news_enrich

> **Status:** canonical component guide · **Verified against:** `7723918`

`apps.news_enrich` owns scrape request decoding, fetch/extraction service behavior, replay/requeue, PostgreSQL worker integration, and schema-valid `scraped_article.v1` output. It does not own acquisition grouping, editorial generation, publication, or rendering.

| Interface | Input | Output/consumer |
|---|---|---|
| batch/service | scrape-request-shaped record | `scraped_article.v1` bus record |
| worker | PostgreSQL queue plus `PG_DSN`/`BATCH` | result bus plus queue status under worker semantics |
| replay/requeue | stable stage/key or failed jobs | another owner-service attempt, not a new identity |
| access index | scraped-article bus | compact enrich status index |

**Invariants:** preserve `index_id`/source provenance; validate bus records; normalize fetch outcome and error fields; keep credentials out of artifacts; retries do not transfer ownership to wrappers. Failures are explicit result/queue states rather than fabricated content.

The canonical invocation surface is the owner entrypoint; the generic minimal-loop enrich branch currently references an absent compatibility script. **Tests:** enrich service, access-index, and owner migration/characterization tests where present.

Extend the service/records/bus-writer seam, not archive or compatibility code. See [status/error semantics](../reference/status-and-error-semantics.md) and [storage](../reference/buses-indexes-and-storage.md).
