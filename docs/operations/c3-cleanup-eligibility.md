# C3 cleanup eligibility manifest

> **Status:** proposal only · **C2 does not delete anything** · reconciled with 2026-09-06 host acceptance

Evidence basis: host C1 census plus the 2026-09-06 C2 acceptance/replay-governance study, the canonical artifact/state architecture, and the C2 producer/consumer trace.

The purpose of this file is to make later cleanup mechanical and reviewable. Before any `apply`, the host must regenerate exact path/byte counts from the then-current estate and satisfy the replay/durability gates below.

## Eligibility table

| surface | observed footprint / evidence | C2/C3 classification | cleanup precondition | durable-copy requirement | notes |
|---|---:|---|---|---|---|
| historical `storage/buses/news_ref/v1/news_ref_*.jsonl` snapshots | 3,330 files / 38,393,640,146 logical B | `UNKNOWN_NEEDS_JUDGMENT` | define replay horizon and either prove arbitrary-old reconstruction from canonical immutable inputs or create/verify a cold archive | required before destructive action unless reconstruction is proven for the retained horizon | complete materialized reference states; no normal production consumer requires every historical copy, but arbitrary historical replay is not yet proven |
| `storage/buses/news_ref/v1/news_ref_current.jsonl` | C2 real-data canary: 24,188,331 B | `RETAIN_HOT` | never part of historical cleanup | no | sole current materialization |
| new C2 `storage/buses/news_ref/v1/manifest_*.json` plus run/control records | unchanged real-data cycle added only 3,493 B total control/audit state | `RETAIN_RECENT` | choose explicit diagnostic/audit retention | optional if another durable evidence store is adopted | hashes/change counts; no full payload multiplication |
| selected historical `news_ref` checkpoints after replay policy exists | gzip sample ratio ~0.407–0.427; sample mean ~0.422 | `ARCHIVE_COLD` or `RECONSTRUCTIBLE_RECLAIM_CANDIDATE` | select checkpoint cadence from explicit replay/recovery contract; verify archive or reconstruction | yes if retained as sole historical recovery path | compressed checkpoints are storage-efficient, but adequacy is not yet proven |
| dated `storage/indexes/news_recent_refs_*` excluding `_latest` | within historical index estate | `RECONSTRUCTIBLE_RECLAIM_CANDIDATE` | re-audit exact globs; prove no external/manual consumer; preserve latest pointers; consumer parity green | none normally | derived read models; C2 stops creating new dated copies |
| dated `storage/indexes/news_recent_groups_*` excluding `_latest` | within historical index estate | `RECONSTRUCTIBLE_RECLAIM_CANDIDATE` | same as above | none normally | derived read models |
| `storage/indexes/news_recent_refs_latest.jsonl` | current read model | `RETAIN_HOT` | exclude from cleanup | none | operational, reconstructible current read model |
| `storage/indexes/news_recent_groups_latest.jsonl` | current read model | `RETAIN_HOT` | exclude from cleanup | none | operational, reconstructible current read model |
| other dated PR3A indexes / compact summaries | exact C3 bytes TBD | `RETAIN_RECENT` | choose diagnostic retention; verify latest pointers survive | no current requirement | small evidence/control records; keep separate from large read-model snapshots |
| `storage/runs/` | 2,889,466 logical B / 3,439 files in C1 | `RETAIN_RECENT` | choose diagnostic retention | no current requirement | small bytes, high file count |
| `storage/observability/` | 54,516,950 logical B / 56,094 files in C1 | `RETAIN_RECENT` | choose retention aligned with debugging/publication evidence needs | optional | evidence only, never product truth |
| finalized `artifacts/sensing_runs/runs/<run_id>` / `storage/sensing_compacted/generations/<generation>` when present | absent from the local acceptance estate | `CANONICAL_IMMUTABLE_EVIDENCE` | no cleanup without separate evidence-retention decision | yes unless another verified durable copy exists | architecture identifies these as the intended immutable recovery path |
| `storage/buses/news_digest_group/` | ~159 MB class observed in C1 | `UNKNOWN_NEEDS_JUDGMENT` | separate semantic/retention study | unknown | C2 deliberately does not redesign this bus |
| `data/master_ref.csv` / `data/master_index.csv` and other `data/` subfamilies | C1 data total ~290 MB | `UNKNOWN_NEEDS_JUDGMENT` | reconstructibility proof per producer and historical-role classification | depends on subfamily | mutable/transitional Level-0 state; latest semantic reconstruction succeeded but old-state retention remains unproven |
| `legacy/data/` | ~1.08 GB C1 logical | `ARCHIVE_FIRST` | identify remaining consumer and authoritative replacement | yes before deletion unless proven reconstructible elsewhere | historical/compatibility surface; outside C2 |
| `exports/` | ~109 MB C1 logical | `UNKNOWN_NEEDS_JUDGMENT` | establish producer, purpose and whether user-authored | unknown | untracked local surface; never delete merely because generated-looking |
| repo-local `.vercel/.next` and Python caches | ~109.7 MB allocated in C1 | `SAFE_TO_REMOVE_WHEN_REBUILD_PROVEN` | separate cache cleanup plan | no | not domain data |

## What C2 acceptance now proves

The real-data host canary proved:

- `news_ref` is a complete materialized reference state keyed by `index_id`, not an event log or delta;
- the current payload is about 24.19 MB for 32,278 rows;
- an unchanged cycle under a different digest retained no second full payload and added only 3,493 bytes of small evidence/control metadata;
- one selected historical payload (`20260825T05`) was semantically reconstructed exactly as 32,278 ordered parsed rows without using that historical snapshot as an input;
- current production source has no evidenced code path requiring all 3,330 historical full snapshots.

These facts accept C2 for future bounded storage. They do **not** authorize deleting the historical corpus.

## Why the 38.4 GB historical corpus remains unresolved

Arbitrary old-digest replay is still unproven because the local acceptance estate had no immutable historical sensing run bundles or compacted generations, no explicit replay-retention horizon exists, no canonical cold copy was evidenced, and historical code/config/feed identity required for arbitrary-old reconstruction was not shown to be retained.

Therefore the 38.394 GB historical `news_ref` corpus is **not presently a destructive C3 candidate**. It is a high-value governance target whose likely future outcomes are one or more of:

- bounded recent hot checkpoints;
- compressed immutable cold checkpoints;
- reconstructible reclaim candidates once canonical immutable replay is demonstrated;
- retained evidence for a deliberately chosen replay horizon.

## Candidate policy sizes from host evidence

These are planning estimates only, not implemented policy:

| policy | selected historical snapshots | historical JSONL bytes | current hot JSONL | estimated gzip cold bytes | conditional historical reclaim candidate |
|---|---:|---:|---:|---:|---:|
| current only | 0 | 0 | 24,188,331 | 0 | 38,393,640,146 |
| current + all last 7 calendar days | 27 | 665,448,591 | 24,188,331 | n/a | 37,728,191,555 |
| current + all last 30 calendar days | 139 | 3,255,526,091 | 24,188,331 | n/a | 35,138,114,055 |
| current + one checkpoint/day | 57 | 715,880,668 | 24,188,331 | n/a | 37,677,759,478 |
| last 30 days + one checkpoint/week before then | 150 | 3,408,142,006 | 24,188,331 | n/a | 34,985,498,140 |
| current hot + gzip one/day checkpoints | 57 | 715,880,668 uncompressed | 24,188,331 | ~302,294,180 | conditional only |
| current hot + gzip last30/weekly-older checkpoints | 150 | 3,408,142,006 uncompressed | 24,188,331 | ~1,439,151,846 | conditional only |
| full historical snapshots compressed | 3,330 | 38,393,640,146 | n/a | ~16.21 GB estimated | none without policy change |

The gzip values use the measured sample mean ratio (~0.422) and are estimates, not archived bytes.

## Required replay-governance gate before historical `news_ref` deletion

Before any historical `news_ref` payload is moved from `UNKNOWN_NEEDS_JUDGMENT` to `RECONSTRUCTIBLE_RECLAIM_CANDIDATE`, establish all of:

1. an explicit replay-retention horizon;
2. the canonical immutable inputs for that horizon;
3. retained checksums and digest/run identity;
4. retained code/config/feed identity sufficient to reproduce the projection;
5. at least one representative genuinely older replay from those immutable inputs in isolated state;
6. semantic comparison against the historical materialization;
7. a decision whether replay comes from canonical evidence, a verified cold archive, or both.

A latest-state reconstruction from mutable current `master_ref` is useful evidence but is not a substitute for this gate.

## Required cleanup protocol

Any later C3 cleanup must be:

`audit -> plan -> dry-run -> apply`

The dry-run output must enumerate each candidate path, classification/reason, bytes and total reclaim estimate. `apply` must consume the reviewed plan rather than rediscovering candidates with an ad-hoc shell glob.

Hard exclusions until separately approved:

- `news_ref_current.jsonl`;
- historical `news_ref_*.jsonl` while replay/durability gate is unresolved;
- all `*_latest` operational pointers/read models;
- canonical finalized sensing runs / compacted generations where they are the only durable evidence;
- user-authored/unclassified `exports/`;
- `legacy/data/` before archive/reconstructibility proof;
- any only durable copy of finalized evidence.

## C3 gate

Do not apply cleanup until all are true:

1. C2 PR is merged and its CI is green;
2. C2 real-data boundedness remains accepted;
3. production/C0 liveness is not being debugged through the same local state;
4. host re-audit produces exact current candidate bytes;
5. each proposed deletion class has no unresolved `UNKNOWN_NEEDS_JUDGMENT` status;
6. deletion plan explicitly excludes current hot state and canonical immutable evidence;
7. dry-run is reviewed before mutation.

No cleanup action is authorized by this document.