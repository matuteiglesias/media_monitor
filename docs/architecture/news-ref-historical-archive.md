# `news_ref` historical archive strategy

> **Status:** designed from local-corpus evidence; archive construction and C3 deletion remain separate, human-reviewed work.
> **Verified against:** local estate on 2026-09-23; current producer `scripts/export_pr3a_buses.py`, resolver `scripts/build_news_access_indexes.py`, and `contracts/schemas/news_ref.v1.json`.

## Decision

Do not make the live `news_ref.v1` consumer accept historical variation. Keep
C2's bounded `news_ref_current.jsonl` as the sole hot runtime representation.
Create a cold, self-verifying archive in a separate root, using a typed
Parquet/Zstd record-version store plus JSONL manifests and an opaque-payload
quarantine. DuckDB may be used as an optional, zero-server reader; it is not a
runtime dependency. Do not delete a legacy input until that archive has passed
the verification gates below.

This complements, rather than redoes, [C2 bounded storage](c2-bounded-storage.md)
and supplies the archive prerequisite called out by [C3 cleanup eligibility](../operations/c3-cleanup-eligibility.md).

## What the local estate shows

The exact legacy glob (`news_ref_*.jsonl`, excluding `news_ref_current.jsonl`)
contained **3,330 files and 38,393,640,146 bytes** (35.76 GiB) on the inspected
host.  The representative latest legacy state contains 32,278 rows and
24,930,725 bytes. The current C2 state is separate and was not included.

The full raw-file count/byte census is exact. A read-only streaming semantic
census tool is included below; a three-era audit (first, middle and latest)
is recorded in [the small audit artifact](../reference/evidence/news-ref-historical-archive-sample-20260923.json).
It found 70,869 rows, 56,055 identities and 56,395 identity/content versions:
20.42% of row observations were repeats even across those widely separated
states. The middle state is not a continuation of the first, so it is not a
substitute for consecutive-change statistics.

An adjacent early trio was byte-identical (same SHA-256), while its filenames
differed. This proves that duplicate full snapshots exist. The semantic tool
canonicalizes each object as UTF-8 compact JSON with sorted object keys and
unchanged array order, then hashes `index_id`/row-hash pairs in sorted identity
order. Whitespace and object-key order cannot become false changes; values,
types, keys and array order can.

The contract-shaped sample used all 12 current fields and found no historical-
only fields. This is not evidence that the full estate has no drift: one
mid-era file, `news_ref_20260423T210615Z.jsonl`, has a truncated final JSON row
(line 16,515). That row is evidence that an archive must retain a raw,
quarantined path rather than silently dropping or coercing invalid history.

In the three-era sample, URL values accounted for 31,787,210 of 42,201,500
canonical unique-row bytes (75.3%). Repeated full materialization and long
Google News URLs are therefore more important than JSON property-name syntax
alone.

## Physical-format evidence

On `news_ref_20260825T050926Z.jsonl` (24,930,725 B / 32,278 rows):

| representation | bytes | ratio | finding |
|---|---:|---:|---|
| legacy JSONL | 24,930,725 | 1.000 | source |
| gzip level 6 | 10,627,641 | 0.426 | baseline; preserves exact legacy bytes |
| zstd level 6 | 10,000,769 | 0.401 | faster cold compression; optional tool dependency |
| Parquet/Zstd level 6, `meta` serialized as `meta_json` | 9,837,965 | 0.395 | small additional saving for a single full state |

Direct Arrow inference cannot write the all-empty `meta` struct in this sample.
That is a concrete schema-drift/physical-layout reason to store common typed
columns plus `extras_json`/`raw_payload`, not to expose historical rows directly
as the current contract. The earlier C2 gzip sample mean (0.422) is consistent
with this measurement. Extrapolating only the gzip baseline gives about
16.21 GB for all full snapshots; that retains the pathological snapshot count.
Parquet alone is not the principal answer.

## Archive model and replay semantics

Archive root (outside the live `storage/` tree):

```text
news_ref_archive/v1/
  manifests/<legacy-filename>.json
  record_versions/part-*.parquet
  snapshot_events/part-*.parquet
  checkpoints/<ordinal>.parquet.zst
  quarantine/<content-sha256>.jsonl.zst
```

`record_versions` contains `index_id`, `content_sha256`, `first_observed`,
`last_observed`, typed common columns, `source_schema`, `migration_status`,
`extras_json`, and (when needed) `canonical_payload`. `extras_json` preserves
unknown historical keys; `canonical_payload` or the quarantine object preserves
losslessly any row that cannot safely project. Statuses are `current-valid`,
`migratable`, `legacy-preserved`, and `malformed-quarantined`.

`snapshot_events` is an event log keyed by snapshot ordinal: `add`, `change`,
and `remove`, with the target version hash. A manifest retains original filename,
raw SHA-256, canonical state SHA-256, source byte/row counts, and event range.
An event log is sufficient for exact logical state replay; SCD2 intervals alone
are not sufficient when a record disappears and later reappears or when exact
run ordering matters. Checkpoints every 100 snapshots bound replay to 99 event
segments; they are an access optimization, not a second authority.

“Reconstruct snapshot X” means rebuild its mapping of `index_id` to canonical
row payload (plus the raw quarantined rows belonging to X), then require equal
row count, identity set, per-identity content hashes, canonical state SHA-256,
and manifest raw checksum. JSON whitespace/key order is explicitly outside that
semantic equality definition.

## Candidate assessment

| option | preserves old bytes | fixes repeated state | live dependency | recommendation |
|---|---:|---:|---:|---|
| gzip/zstd each JSONL | yes | no | none | emergency baseline only |
| Parquet each full snapshot | with payload/extras | no | optional reader | useful control benchmark, not final form |
| record versions + events | yes, with payload/quarantine | yes | none | logical source of truth |
| checkpoint + deltas | yes | yes | none | physical replay layout |
| SQLite | possible, but weak compression/schema-evolution fit | yes | sqlite library | staging/verification only |
| Parquet + optional DuckDB | yes | yes | no daemon | recommended cold representation/query layer |

The full-estate archive size cannot honestly be claimed until the complete
version/event build runs. A useful planning envelope is **well below 16.21 GB**
(the full-gzip baseline), with record versions plus events expected to dominate
the savings. The audited three-era sample is deliberately not extrapolated to
the whole estate because state turnover was substantial across that wide span.

## Migration and safety gates

1. Run `python3 scripts/audit_news_ref_history.py --output /tmp/news-ref-audit.json` against the complete estate; preserve its JSON evidence.
2. Construct the archive in a new immutable destination; never write below the
   legacy bus directory.
3. Replay an old, middle and recent snapshot, plus every quarantined row, and
   compare the five equality measures above.
4. Independently scan manifests/checksums and run DuckDB/Parquet queries for
   one record history, one snapshot and a time range.
5. Produce a path-by-path deletion plan. Only human review may move C3 entries
   from `UNKNOWN_NEEDS_JUDGMENT` to eligible. Cleanup is a separate change.

Rollback is trivial before cleanup: reject the archive and retain the original
files. After eventual cleanup, rollback means restoring only the reviewed,
checksummed immutable legacy copy—not regenerating from mutable current state.

## Runtime boundary

No current pipeline code should read this archive by default or relax
`news_ref.v1`. The existing explicit archive resolver boundary in
`scripts/build_news_access_indexes.py` is the correct shape: historical access
must name a snapshot/archive root and verify its manifest. Archive tooling owns
schema accommodation; C2's producer and current consumers remain clean.
