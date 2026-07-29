# AWS Media Monitor Sensing Retrofit — Starting Context v0.1

## Repository

`matuteiglesias/media_monitor`

## Product slice

Only the sensing path:

```text
bin/run_minimal_loop_once.sh --lane sensing
  → s01
  → s02
  → s03
  → export-pr3a
  → build-news-access-indexes
```

Editorial, enrich, article promotion, site snapshots, and Vercel deployment are outside this retrofit.

## Components to inspect first

- `bin/run_minimal_loop_once.sh`
- `scripts/run_with_run_record.py`
- `Makefile`
- `apps/news_acquire/src/news_acquire/stage01_digests.py`
- stage02 and stage03 modules
- acquisition `db.py`, `ids.py`, and I/O helpers
- `scripts/export_pr3a_buses.py`
- `scripts/build_news_access_indexes.py`
- sensing runbooks and README sections
- observability/status contracts and tests
- current systemd/heartbeat helpers

## Existing semantics to preserve

1. `DIGEST_AT` anchors deterministic time windows.
2. Stable IDs prevent accidental duplicate article identity.
3. Invalid rows are quarantined rather than silently accepted.
4. Sensing is failure-isolated from editorial and enrich.
5. Contract buses/indexes are product outputs; raw runtime files are not automatically public contracts.
6. A failed sensing run must remain diagnosable.
7. Human/editorial publication remains outside sensing.

## Findings to verify in PR-A0

These are hypotheses to characterize, not patch immediately:

- DB finish bookkeeping calls may not match the helper signature and may be silently suppressed;
- `DRY_RUN` may conflate network, persistence, and enqueue semantics;
- run-record and outer shell layers may both write lane-latest state;
- local JSONL append and mutable latest files are unsafe analogies for S3;
- cumulative master/index outputs have multiple mutation modes;
- RSS feed configuration is currently embedded in code;
- repeated same-digest execution needs an explicit idempotency rule.

## Human gates

The reviewer must approve:

- A0 writer/side-effect inventory;
- A1 repaired local semantics;
- A2 immutable bundle shape;
- A3 compactor ownership;
- A5 IAM/network/cost boundary;
- A6 final market claim.

## First one-hour Codex task

Execute `PR-A0` only.

The task should leave a trustworthy mutation map and characterization suite. It must not add AWS infrastructure.
