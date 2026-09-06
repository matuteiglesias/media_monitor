# C3 cleanup eligibility manifest

Status: proposal only. **C2 does not delete anything.**

Evidence basis: host C1 census captured 2026-09-06 from `/home/matias/repos/media_monitor` plus the canonical artifact/state architecture and C2 producer/consumer trace.

The purpose of this file is to make later cleanup mechanical and reviewable. Before `apply`, the host must regenerate exact path/byte counts from the then-current estate and prove the C2 replacement is accepted.

## Eligibility table

| surface | C1 observed footprint | C2/C3 classification | cleanup precondition | durable-copy requirement | notes |
|---|---:|---|---|---|---|
| historical `storage/buses/news_ref/v1/news_ref_*.jsonl` snapshots | `news_ref` family 38,397,003,203 logical B | `SAFE_TO_REMOVE_AFTER_C2_ACCEPTANCE` except new `news_ref_current.jsonl` | C2 merged; clean checkout production proves current payload + access-index parity; exact candidate list excludes current | none currently evidenced | legacy full-state copies are not required by current consumers; C2 preserves per-cycle hash/change evidence going forward |
| `storage/buses/news_ref/v1/news_ref_current.jsonl` | new C2 surface | `RETAIN_LATEST` | never part of historical glob deletion | no | sole current materialization |
| `storage/buses/news_ref/v1/manifest_*.json` | new/small | `RETAIN_BOUNDED_HISTORY` | retention policy chosen in C3 | optional if local host ceases to be evidence store | contains hashes/change counts, not full payloads |
| dated `storage/indexes/news_recent_refs_*` excluding `_latest` | within 497,124,578 B total indexes | `SAFE_TO_REMOVE_AFTER_C2_ACCEPTANCE` | C2 consumer parity green; exact host glob proves no required consumer | none | derived read models; C2 stops creating new dated copies |
| dated `storage/indexes/news_recent_groups_*` excluding `_latest` | within same indexes total | `SAFE_TO_REMOVE_AFTER_C2_ACCEPTANCE` | same as above | none | derived read models |
| `storage/indexes/news_recent_refs_latest.jsonl` | current read model | `RETAIN_LATEST` | exclude from cleanup | none | reconstructible but operationally required |
| `storage/indexes/news_recent_groups_latest.jsonl` | current read model | `RETAIN_LATEST` | exclude from cleanup | none | reconstructible but operationally required |
| other dated PR3A indexes / compact summaries | part of 497,124,578 B indexes; exact C3 bytes TBD | `RETAIN_BOUNDED_HISTORY` | choose diagnostic retention; verify latest pointers survive | no | small evidence/control records; do not conflate with large read-model snapshots |
| `storage/runs/` | 2,889,466 logical B / 3,439 files | `RETAIN_BOUNDED_HISTORY` | choose diagnostic retention | no current requirement | small bytes, high file count |
| `storage/observability/` | 54,516,950 logical B / 56,094 files | `RETAIN_BOUNDED_HISTORY` | choose retention aligned with debugging/publication evidence needs | optional | evidence only, never product truth |
| `storage/buses/news_digest_group/` | 159,332,750 logical B observed as largest sibling after news_ref | `UNKNOWN / NEEDS_JUDGMENT` | separate semantic/retention decision | unknown | C2 deliberately does not redesign this bus |
| `data/` | 289,694,963 logical B | `UNKNOWN / NEEDS_JUDGMENT` by subfamily | reconstructibility proof per producer | depends on subfamily | Level-0 transitional workspace but some legacy/operator data may merit care |
| `legacy/data/` | 1,080,905,954 logical B | `ARCHIVE_FIRST` | identify remaining consumer and authoritative replacement | yes before deletion unless proven reconstructible elsewhere | historical/compatibility surface; outside targeted C2 change |
| `exports/` | 109,413,914 logical B | `UNKNOWN / NEEDS_JUDGMENT` | establish producer, purpose and whether user-authored | unknown | untracked local surface; never delete merely because generated-looking |
| repo-local `.vercel/.next` and Python caches | ~109.7 MB allocated | `SAFE_TO_REMOVE_WHEN_REBUILD_PROVEN` | separate cache cleanup plan | no | not domain data; C3 may handle separately |

## Reclaimable-byte posture

The dominant reclaim candidate is the legacy timestamped `news_ref` payload family: approximately 38.397 GB logical in the C1 census. C3 must remeasure the exact glob after C2 acceptance and subtract any file explicitly retained/current before claiming a final reclaim number.

Do not treat the full 497 MB `storage/indexes/` footprint as reclaimable. It contains `combined.jsonl`, latest pointers and other records that require separate classification.

## Required cleanup protocol

C3 cleanup must be implemented as:

`audit -> plan -> dry-run -> apply`

The dry-run output must enumerate each candidate path, reason/classification, bytes and total reclaim estimate. `apply` must consume the reviewed plan rather than rediscovering candidates with an ad-hoc shell glob.

Hard exclusions until separately approved:

- `news_ref_current.jsonl`;
- all `*_latest` operational pointers/read models;
- user-authored/unclassified `exports/`;
- `legacy/data/` before archive/reconstructibility proof;
- any only durable copy of finalized evidence.

## C3 gate

Do not apply cleanup until all are true:

1. C2 PR merged and its CI is green;
2. at least one representative local canary proves bounded current storage on real data;
3. production/C0 liveness is not being debugged through the same local state;
4. host re-audit produces exact current candidate bytes;
5. deletion plan has an explicit current-file exclusion and no unresolved `UNKNOWN` path;
6. dry-run is reviewed before mutation.
