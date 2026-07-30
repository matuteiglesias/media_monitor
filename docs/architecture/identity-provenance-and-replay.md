# Identity, provenance, and replay

> **Status:** canonical architecture · **Verified against:** `bf04a74`

## Identity hierarchy

| Identity | Derivation | Purpose |
|---|---|---|
| `digest_at` | UTC `YYYYMMDDTHH` | logical hour shared across stages |
| logical sensing run | `sensing:<digest_at>` | groups retry attempts |
| physical `run_id` | `sensing:<digest_at>:attempt:<n>:<unique>` unless supplied | immutable evidence namespace |
| `index_id` | normalized title/source/URL hash in owner ID code | stable sensed-news identity |
| compaction generation | hash of accepted run fingerprints and rejected reasons | reproducible canonical state identity |
| `article_id` | SHA-1 suffix over digest, draft ID, slug | stable promoted-article identity |
| site `snapshot_id` | SHA-256 of canonical snapshot excluding `snapshot_id` and `generated_at` | stable deployment content identity |

## Provenance chain

A sensing manifest records source commit, optional image digest, feed/config and input digests, stage results, output paths, checksums, counts, quarantine, and failure code. Compaction validates every declared checksum and records accepted/rejected runs plus generation checksums. The site snapshot records source index paths/hashes and Git SHA. Published articles retain draft ID, digest, story group, citations, source links, review status, and timestamps.

## Replay rules

1. A retry gets a distinct physical `run_id`; it never overwrites earlier evidence.
2. Re-uploading an immutable S3 key is safe only when existing bytes match.
3. `FINALIZED` is written/uploaded last and is eligibility, not merely process exit.
4. For the same digest, deterministic ordering chooses one attempt. Re-running compaction over identical evidence yields the same generation ID/content.
5. Generation objects land before `current.json`; readers never follow a pointer to an incomplete generation.
6. Derived indexes/snapshots may be rebuilt from authoritative buses/indexes. Their mutable paths are not stable fact identities.
7. Human approval is not replayed implicitly. Re-promotion validates the selected draft and deterministic article identity, but remains an explicit operator action.

## Reconciliation checks

Do not accept success from exit zero alone. Reconcile manifest status, `FINALIZED`, checksums, candidate presence, selected run IDs, generation manifest, pointer target, schema validation, source hashes, and—when operating in cloud—logs and expected IAM denial.
