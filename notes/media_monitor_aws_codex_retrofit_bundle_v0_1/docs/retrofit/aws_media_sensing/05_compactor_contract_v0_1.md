# Deterministic Sensing Compactor Contract v0.1

## Ownership

The compactor is the sole selector and publisher of canonical cumulative/latest
sensing state. Producers write immutable bundles only. The legacy compatibility
adapter may mirror the already-selected generation but cannot select a bundle.

## Selection

1. Discover finalized run directories.
2. Validate manifest identity, eligible status, required candidates, and every
   producer checksum.
3. Reject error, incomplete, checksum-invalid, or structurally invalid bundles.
4. Deduplicate repeated input paths and run IDs.
5. For each `digest_at`, accept exactly one attempt ordered by
   `(digest_at, completed_at, run_id)`.
6. Order accepted digest winners by the same key; the last winner owns recent
   refs/groups and lane-latest status.

Input enumeration order never affects the result. Replaying the same input set
produces the same generation and does not rewrite the current pointer.

## Cumulative state

`master_ref.csv` is recomputed from every accepted digest winner. Stable
`index_id` is the deduplication key. `first_seen` is the minimum non-empty value,
`last_seen` is the maximum, and remaining row fields come from the deterministic
highest-ranked observation. Thus an out-of-order completion cannot regress or
discard an older accepted identity.

Recent refs/groups come only from the newest accepted digest winner. Empty
candidates remain valid empty canonical indexes.

## Atomic publication

```text
<state-root>/
  .compactor.lock
  generations/<deterministic-generation>/
    master_ref.csv
    news_recent_refs.jsonl
    news_recent_groups.jsonl
    accepted_runs.json
    lane_status.json
    manifest.json
  current.json
```

One OS file lock enforces a local single writer. A generation is built in private
staging and renamed into `generations/`. `current.json` is fsynced and atomically
replaced only after the complete generation exists. A build/validation failure
leaves the prior pointer unchanged.

The generation identity includes accepted bundle fingerprints and normalized
rejections. Duplicate invocation with unchanged inputs is byte-idempotent.
