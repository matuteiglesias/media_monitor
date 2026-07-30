# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A3`
- Status: `ACCEPTED`
- Base commit: `0e2cae8`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Added the sole deterministic local owner of cumulative master state, recent refs/groups, accepted-run history, and lane-latest status over immutable sensing bundles.

## Files and surfaces changed

- `compactor.py`: discovery, validation, deterministic planning, cumulative merge, single-writer lock, immutable generation construction, and atomic pointer publication.
- `compact_sensing_bundles.py` and Make target: operator entrypoint.
- Compatibility promoter now mirrors only the compactor-selected generation and cannot select bundles.
- Compactor contract, runbook, carry state, and focused compactor tests.

## Invariants preserved

- Stable `index_id` remains the cumulative master deduplication key.
- Immutable producer bundles are never modified.
- Error/incomplete/invalid bundles remain diagnostic evidence and never become canonical state.
- Editorial, enrich, site, scheduler, and AWS surfaces are untouched.

## Decisions made

- One winner per `digest_at` is selected by `(digest_at, completed_at, run_id)`; enumeration order is irrelevant.
- Cumulative master state is recomputed across all accepted digest winners, preventing out-of-order completion from regressing identities.
- Recent refs/groups and lane latest come only from the newest accepted digest winner.
- Canonical publication is an immutable generation plus one atomically replaced `current.json` pointer under a local single-writer lock.
- Generation identity includes accepted fingerprints and normalized rejections. An unchanged duplicate invocation does not rewrite the pointer.
- The compatibility adapter has no selection authority and can only mirror `current.json`.

## Acceptance evidence

- Commands:
  - `pytest -q tests/test_sensing_compactor.py tests/test_sensing_run_bundle.py tests/test_build_news_access_indexes.py`
  - `python -m compileall -q apps/news_acquire/src/news_acquire scripts/compact_sensing_bundles.py scripts/promote_sensing_bundle_local.py`
  - `git diff --check`
- Tests:
  - Out-of-order bundle enumeration selects the newest digest and preserves cumulative identities.
  - Duplicate paths and duplicate invocations are idempotent.
  - Replay attempts select exactly one deterministic winner per digest.
  - Error/checksum-invalid bundles are rejected without latest-state regression.
  - Failed generation construction leaves the prior pointer byte-unchanged.
  - Legacy mirroring requires a compactor current pointer.
- Runtime artifacts:
  - Tests materialize immutable producer bundles, compact generations, current pointers, cumulative CSV, recent indexes, accepted history, and lane status.
- Failure checks:
  - Checksum tampering is rejected.
  - Malformed candidate JSON aborts staging without pointer replacement.
- Known warnings:
  - Local locking uses POSIX `flock`; cloud single-writer enforcement belongs to later AWS deployment work.
  - Repository-wide legacy `backend` import collection failures remain outside this PR.

## Deviations from embryo plan

none

## Remaining blockers

- Human approval of deterministic replay winner and cumulative merge semantics.
- S3 adapters and cloud-safe task entrypoint are intentionally absent until PR-A4.

## Next PR entry conditions

- PR-A3 is accepted.
- `sensing_compaction.v1` generation and pointer contracts are frozen for storage adapters.
- PR-A4 implements adapters/container/task seams only and does not change selection semantics.

## Exact re-entry command or first inspection

```bash
pytest -q tests/test_sensing_compactor.py && cat notes/media_monitor_aws_codex_retrofit_bundle_v0_1/docs/retrofit/aws_media_sensing/prompts/PR-A4.md
```

## Do not reopen

- Producers do not own cumulative/latest state.
- The compatibility mirror is not a compactor and cannot select a run.
- Exactly one deterministic attempt wins per digest.
- Atomic canonical visibility occurs only through `current.json`.

## Proposed carry-state update

- `current_pr`: `PR-A3`
- `status`: `REVIEW`
- `last_accepted_pr`: `PR-A2`
- `next_pr`: `PR-A4` after human acceptance; retain `PR-A3` while under review
- `blockers`: `["Human approval of PR-A3 deterministic selection and publication contract"]`
