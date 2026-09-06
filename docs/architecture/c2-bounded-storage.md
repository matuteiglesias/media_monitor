# C2 bounded storage semantics

> **Status:** accepted by real-data host canary · implementation on `hardening/c2-bounded-storage` · pending merge

## Decision

`news_ref.v1` is a logical contract over reconciled current reference state. It is not an immutable full-state snapshot per scheduler cycle.

The physical local representation is therefore bounded:

- `storage/buses/news_ref/v1/news_ref_current.jsonl` — sole current materialization, atomically replaced only when content changes;
- `storage/buses/news_ref/v1/manifest_<export_at>.json` — small per-cycle evidence containing digest/run identity, source, row count, content hash, previous hash, payload bytes and identity change counts;
- `storage/indexes/news_recent_refs_latest.jsonl` — replaceable derived read model;
- `storage/indexes/news_recent_groups_latest.jsonl` — replaceable derived read model.

The `news_ref.v1` JSON Schema remains the logical row contract. C2 changes persistence, not the contract consumed by downstream code.

No existing historical payload is deleted by C2.

## Producer / consumer map

| surface | logical authority | producer | direct consumers | history required? | reconstructibility / evidence rule |
|---|---|---|---|---|---|
| `data/master_ref.csv` / `data/master_index.csv` | Level-0 working state | acquisition/index stages | PR3A bus exporter | no storage authority claimed here | transitional/rebuildable workspace |
| `storage/buses/news_ref/v1/news_ref_current.jsonl` | current `news_ref.v1` materialization | `scripts/export_pr3a_buses.py` | `scripts/build_news_access_indexes.py` | current state only | replaceable from upstream state; manifest hashes identify each observed state |
| `storage/buses/news_ref/v1/manifest_*.json` | per-cycle export evidence | `scripts/export_pr3a_buses.py` | diagnostics/audit; PR3A resolution for current state | yes, small metadata | retained evidence; never treated as historical payload when it points to mutable current state |
| `storage/buses/news_digest_group/v1/*` | contract bus for digest groups | `scripts/export_pr3a_buses.py` | `scripts/build_news_access_indexes.py` | not changed by C2 | existing semantics preserved pending separate retention decision |
| `storage/indexes/pr3a_exports_latest.json` | current export pointer/index | PR3A exporter | access-index builder / diagnostics | latest only | replaceable control/read state |
| `storage/indexes/pr3a_exports_<digest>_<export>.json` | run evidence | PR3A exporter | fallback diagnostics / compatibility | small audit history | may point to mutable `news_ref_current`; must not satisfy historical replay |
| `storage/indexes/news_recent_refs_latest.jsonl` | derived read model | access-index builder | publication guard, editorial selection, story contexts, publish validation, site snapshot/public data | no | atomically replaced; reconstructible from current bus inputs |
| `storage/indexes/news_recent_groups_latest.jsonl` | derived read model | access-index builder | publication guard, editorial/site builders | no | atomically replaced; reconstructible from current bus inputs |
| dated `news_recent_refs_*` / `news_recent_groups_*` | legacy derived snapshots | former access-index behavior | no evidenced required consumer | no | no longer emitted by C2 |
| `apps/news_site/public/data/*` | hardened public projection | site/public-data builders | Next.js public site | latest public snapshot | replaceable from hardened indexes/snapshot builders |

## Storage invariants

1. Repeating an unchanged `news_ref` cycle under a different digest identity must not retain another O(N) payload.
2. There is at most one normal local `news_ref_current.jsonl` authoritative payload per schema version.
3. A changed current state is installed with same-filesystem atomic replacement; a failed replacement leaves the previous authoritative payload intact.
4. Every successful/no-change export records a content SHA-256 and previous content SHA-256 in small evidence metadata.
5. Identity change counts are computed on `index_id`: added, changed and removed.
6. Replaceable `news_recent_*_latest` read models have bounded cardinality and do not emit timestamped copies during normal rebuilds.
7. Historical run metadata that points at `news_ref_current.jsonl` is evidence about a past run, not a historical snapshot; an explicit old-digest replay cannot resolve through that mutable path.
8. Schema validation remains mandatory exactly as before C2.
9. C2 performs no deletion of pre-existing storage.

## Why no database in C2

The observed failure was primarily full-state multiplication, not a demonstrated query/indexing requirement. A bounded JSONL current materialization removes the O(cycles × relation-size) persistence pattern with no server, migration service or new runtime dependency.

SQLite, Parquet or another physical encoding may be evaluated later if keyed mutation, analytical scans, compression or multi-consumer access creates an evidenced requirement. They are not prerequisites for boundedness.

## Physical-encoding evidence

JSONL repeats property names per row, including constant contract metadata. C2 intentionally keeps the logical JSONL row contract stable while fixing the much larger multiplication problem first.

The 2026-09-06 host study measured five historical payloads spread across the corpus. Gzip level 6 reduced them to roughly 40.7–42.7% of plain JSONL size, with a sample mean ratio of about 0.422. This confirms that cold compression is potentially useful, but it is a separate retention decision from C2 boundedness.

## Real-data host acceptance — 2026-09-06

The C2 branch was tested from a disposable clone against the real host `master_ref.csv` while all writes went to isolated `/tmp` state. The original checkout and historical storage remained read-only.

Observed acceptance evidence:

- real source rows: 32,278;
- first synthetic-digest cycle: one `news_ref_current.jsonl`, 24,188,331 bytes;
- second synthetic-digest cycle with identical source state: `skipped_duplicate` / unchanged;
- second-cycle persistent growth: 3,493 bytes total, all small control/audit records;
- second cycle retained zero additional `news_ref` payload bytes;
- manifest change counts on the unchanged cycle: added 0, changed 0, removed 0;
- storage regression suite: 11 focused tests passed;
- GitHub runtime-contract and docs-site CI also passed on the branch.

This proves the primary C2 invariant on real data: an unchanged cycle is O(1) metadata growth rather than O(N) full-state growth.

## Historical semantic recovery rehearsal

A representative historical materialization at digest `20260825T05` was reconstructed in isolated state from the then-current host `master_ref.csv` plus `data/digest_map/20260825T05.csv`, without reading the historical `news_ref` snapshot as an input.

Results:

- historical rows: 32,278;
- reconstructed rows: 32,278;
- ordered parsed JSON rows: exactly equal;
- changed common rows: 0;
- byte hashes differed only because the C2 serializer emits different JSON formatting.

This is evidence that `news_ref` is a complete materialized reference state and that at least the selected latest historical payload is semantically reconstructible.

It is **not** proof of arbitrary historical replay. The host did not contain immutable old sensing run bundles / compacted generations, no explicit replay-retention horizon was defined, and historical code/config/feed identity needed for arbitrary-old reconstruction was not demonstrated.

Therefore C2 is accepted for future bounded storage, while historical-retention policy remains a separate C3/replay-governance decision.
