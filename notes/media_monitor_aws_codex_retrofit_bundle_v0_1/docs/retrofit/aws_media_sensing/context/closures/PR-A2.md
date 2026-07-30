# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A2`
- Status: `ACCEPTED`
- Base commit: `8eded47`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Added a self-contained, replay-safe sensing execution that uses an isolated workspace and finalizes immutable success, partial, empty, or error evidence beneath a unique run ID. Mutable local promotion is a separate compatibility command.

## Files and surfaces changed

- `run_bundle.py`: isolated pipeline execution, run identity, evidence packaging, checksums, manifest, and atomic finalization.
- `run_sensing_bundle.py`: runnable producer CLI with non-zero error-run exit behavior.
- `promote_sensing_bundle_local.py`: explicit local-only promotion adapter.
- Make targets and acquisition runbook commands.
- Run-bundle contract document and focused tests.
- Carry state records human acceptance of PR-A1 and holds PR-A2 at review.

## Invariants preserved

- Existing stable article/digest identity and validation logic remains the implementation used by s01-s03/export.
- Existing local minimal-loop behavior remains available and is not silently redirected.
- Editorial, enrich, article promotion, site, and cloud surfaces are untouched.
- Each sensing attempt still uses the fixed `DIGEST_AT` window.

## Decisions made

- A logical digest may have multiple immutable attempt bundles; `run_id` adds attempt plus UUID identity.
- Finalization uses private staging and a final atomic rename. Existing finalized run IDs fail closed rather than overwrite.
- `FINALIZED` exists for every valid evidence bundle, including errors; status in the manifest determines acceptance eligibility.
- Mutable `latest` filenames are renamed to candidate names while packaging and never appear inside the bundle.
- Local compatibility promotion refuses error bundles and remains explicitly separate from production. Ordering and governed promotion remain PR-A3 work.

## Acceptance evidence

- Commands:
  - `pytest -q tests/test_sensing_run_bundle.py tests/test_sensing_a1_controls.py tests/test_sensing_characterization.py`
  - `bash -n bin/run_minimal_loop_once.sh`
  - `python -m compileall -q apps/news_acquire/src/news_acquire scripts/run_sensing_bundle.py scripts/promote_sensing_bundle_local.py`
  - `ACQUIRE_NETWORK=0 ENQUEUE_SCRAPE=0 DB_RUN_BOOKKEEPING=0 python scripts/run_sensing_bundle.py --digest-at 20260729T00 --run-root "$TMPDIR" --run-id sensing:20260729T00:attempt:1:smoke`
- Tests:
  - Bundle tests cover checksums, candidates, absence of `latest`, error evidence, same-digest attempts, overwrite refusal, and separate promotion.
- Runtime artifacts:
  - Review found and fixed one acceptance defect: an otherwise successful zero-row run was incorrectly failed by strict access-index input resolution. Bundle execution now explicitly permits empty candidate indexes and finalizes `empty_success`; strict legacy index behavior remains the default.
  - The no-network smoke run finalized `empty_success`, returned zero, and contained no mutable `latest` filename.
- Failure checks:
  - Failed run evidence remains finalized and inspectable.
  - Existing run IDs cannot be finalized twice.
  - Error bundles cannot be compatibility-promoted.
- Known warnings:
  - The smoke environment required installing existing runtime dependencies (`feedparser` and `psycopg`) because this repository has no acquisition dependency manifest yet. Pinning belongs to PR-A4.
  - Repository-wide legacy `backend` import collection failures remain outside this PR.

## Deviations from embryo plan

none

## Remaining blockers

- Deterministic selection/promotion across multiple bundles is intentionally absent until PR-A3.

## Next PR entry conditions

- PR-A2 is accepted.
- Bundle manifest/checksum and status semantics are frozen as PR-A3 inputs.
- PR-A3 remains a deterministic local single-writer compactor only; no S3 or infrastructure work.

## Exact re-entry command or first inspection

```bash
pytest -q tests/test_sensing_run_bundle.py && cat notes/media_monitor_aws_codex_retrofit_bundle_v0_1/docs/retrofit/aws_media_sensing/prompts/PR-A3.md
```

## Do not reopen

- Same-digest retries use distinct immutable run IDs.
- Failed attempts retain finalized diagnostic evidence.
- No task-owned `latest` output belongs in a run bundle.
- Local promotion is a compatibility adapter, not the governed compactor.

## Proposed carry-state update

- `current_pr`: `PR-A2`
- `status`: `REVIEW`
- `last_accepted_pr`: `PR-A1`
- `next_pr`: `PR-A3` after human acceptance; retain `PR-A2` while under review
- `blockers`: `["Human approval of PR-A2 bundle contract and replay semantics"]`
