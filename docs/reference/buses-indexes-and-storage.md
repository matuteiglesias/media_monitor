# Buses, indexes, snapshots, and storage

> **Status:** canonical reference · **Verified against:** `7723918`

| Class | Layout/examples | Writer | Semantics |
|---|---|---|---|
| Level 0 | `data/rss_slices`, `digest_map`, `digest_jsonls`, `pf_out`, `drafts`, `quarantine` | owning runtime stage | transitional/rebuildable |
| buses | `storage/buses/<contract>/v1/*.jsonl` | contract producer/exporter | versioned owner seam |
| export evidence | `storage/runs/*`, export manifests | exporter | reconciliation evidence |
| news indexes | `storage/indexes/news_recent_*`, export latest pointers | news index builder | derived mutable read model |
| enrich index | enrich latest/status index | enrich index builder | derived mutable status |
| editorial index | `storage/indexes/editorial_latest.json` | editorial index builder | derived human decision view |
| published indexes | published latest/list/article projections | published index builder | derived from human-approved bus |
| sensing runs | `artifacts/sensing_runs/runs/<run_id>` / S3 runs prefix | producer | immutable, finalized last |
| sensing state | generations plus `current.json` | compactor | immutable generation, mutable pointer |
| handoff | `artifacts/editorial_handoff/latest` | handoff module | operator packet |
| public snapshots | `web/data/*`, `apps/news_site/public/data/*` | named snapshot/refresh builder | allowlisted deploy inputs |
| observability | `storage/observability/*` | named loop/roll recorder | evidence, not product truth |

For writer/replay detail see [artifact state authority](../architecture/artifact-ladder-and-state.md). Readers must consume the lowest appropriate stable layer: owner internals use Level 0, modules use buses, humans/UIs use indexes, and browsers use public snapshots.
