# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A1`
- Status: `REVIEW`
- Base commit: `2befbb2`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Made local sensing controls, feed configuration, DB bookkeeping, and producer telemetry ownership explicit while retaining `DRY_RUN` compatibility. No AWS or immutable-run behavior was introduced.

## Files and surfaces changed

- Added `runtime.py` with independently resolved acquisition, artifact, enqueue, and DB controls.
- Added `feed_config.py` and `config/sensing_feeds.v1.yaml` with schema and value validation.
- Updated s01-s03 to honor explicit artifact/DB controls and to stop suppressing enabled bookkeeping errors.
- Aligned the acquisition DB finish helper with stage metadata calls.
- Made the outer sensing loop the sole owner of the consolidated run record, lane-latest status, and summary; child wrappers retain command manifests/logs.
- Documented operator defaults and compatibility behavior in the acquisition runbook.
- Added A1 control/configuration/ownership tests and updated A0 characterization assertions for repaired semantics.
- Updated carry state to record human acceptance of PR-A0 and hold PR-A1 at `REVIEW`.

## Invariants preserved

- `DIGEST_AT` still anchors deterministic windows and filenames.
- Feed topics and URLs preserve the prior embedded defaults.
- `DRY_RUN=1` still disables network fetch and scrape enqueue while leaving local artifact behavior enabled.
- Stable IDs, validation, and quarantine schemas are unchanged.
- Editorial, enrich, publication, and cloud surfaces are untouched.

## Decisions made

- `ACQUIRE_NETWORK`, `WRITE_ARTIFACTS`, `ENQUEUE_SCRAPE`, and `DB_RUN_BOOKKEEPING` are independent; explicit values override `DRY_RUN` compatibility defaults.
- Postgres bookkeeping is opt-in (`DB_RUN_BOOKKEEPING=0` by default) so the existing Postgres-optional local path remains usable. When enabled, errors are contract failures and propagate.
- Static feeds use versioned `sensing_feeds.v1` YAML. Missing, malformed, empty, duplicate-topic, or non-HTTP(S) configurations fail closed.
- The outer shell owns one lane-level run record and final status. Stage wrappers write per-command log/manifest evidence but do not compete for run-record/latest ownership in this path.

## Acceptance evidence

- Commands:
  - `bash -n bin/run_minimal_loop_once.sh`
  - `python -m compileall -q apps/news_acquire/src/news_acquire scripts/run_with_run_record.py`
  - `pytest -q tests/test_sensing_characterization.py tests/test_sensing_a1_controls.py tests/test_stage02_master_index_update.py tests/test_export_pr3a_buses.py tests/test_build_news_access_indexes.py tests/test_news_editorial_briefs_pipeline.py tests/test_news_enrich_service.py`
  - `pytest -q`
- Tests:
  - 36 targeted sensing, export/index, editorial, and enrich tests passed.
  - Independent control resolution, compatibility overrides, invalid configuration, artifact-free enqueue, strict DB failure, and telemetry ownership are covered.
- Runtime artifacts:
  - Wrapper tests execute real child processes and verify manifest/run-record/status boundaries.
- Failure checks:
  - Invalid feed configurations raise before acquisition.
  - Explicitly enabled DB bookkeeping failures propagate.
  - Failed child commands retain logs and manifests.
- Known warnings:
  - Repository-wide collection still fails in legacy `tests/test_ids.py` and `tests/test_models.py` because they import the removed `backend` package. This predates A1 and is outside its sensing-only boundary.

## Deviations from embryo plan

none

## Remaining blockers

- Human approval of PR-A1 local compatibility defaults and the outer-orchestrator ownership decision.
- Repository dependency installation remains informal; container dependency pinning belongs to PR-A4, not A1.

## Next PR entry conditions

- PR-A1 is accepted by a human reviewer.
- The four side-effect controls and feed schema are treated as the local compatibility contract.
- PR-A2 confines work to per-run roots and immutable sensing bundles; it must not add AWS adapters or the compactor.

## Exact re-entry command or first inspection

```bash
pytest -q tests/test_sensing_characterization.py tests/test_sensing_a1_controls.py && cat notes/media_monitor_aws_codex_retrofit_bundle_v0_1/docs/retrofit/aws_media_sensing/prompts/PR-A2.md
```

## Do not reopen

- Feed defaults are versioned in `config/sensing_feeds.v1.yaml`.
- `DRY_RUN` is a compatibility alias, not the canonical side-effect control.
- DB bookkeeping is optional by default and strict when explicitly enabled.
- The outer sensing orchestrator owns the lane run record and latest status.

## Proposed carry-state update

- `current_pr`: `PR-A1`
- `status`: `REVIEW`
- `last_accepted_pr`: `PR-A0`
- `next_pr`: `PR-A2` after human acceptance; retain `PR-A1` while under review
- `blockers`: `["Human approval of PR-A1 local sensing semantics and configuration"]`
