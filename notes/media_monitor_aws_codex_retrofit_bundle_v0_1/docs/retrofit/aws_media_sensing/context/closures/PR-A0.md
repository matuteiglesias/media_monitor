# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A0`
- Status: `REVIEW`
- Base commit: `09cfb13200449c4a50cdb0a7a58671fb36bbfa57`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Installed the supplied retrofit governance surface and characterized the existing sensing lane without changing runtime behavior. The writer inventory now traces the canonical five-command sensing sequence, all identified filesystem/DB/status mutations, retry behavior, and partial-failure behavior. Focused tests make the most important defects and semantics executable evidence.

## Files and surfaces changed

- `03_writer_side_effect_inventory_v0_1.md`: execution controls, writer/owner/mutation map, retry/failure effects, and proven repair targets.
- `tests/test_sensing_characterization.py`: same-digest replacement, DB finish signature, `DRY_RUN`, failed-wrapper evidence, and duplicate status-owner characterization.
- `context/closures/PR-A0.md`: this review closure and proposed carry transition.
- No production code, configuration, AWS surface, or non-sensing product lane changed.

## Invariants preserved

- `DIGEST_AT` remains the deterministic sensing-window anchor.
- Stable article/digest identity code is untouched.
- Existing quarantine and failure-isolation behavior is untouched.
- Editorial, enrich, article promotion, `news_site`, and Vercel are untouched.
- Current local/systemd compatibility behavior is unchanged.

## Decisions made

- Treat same-digest execution as mutable replay characterization, not idempotent immutable-run semantics: several outputs replace in place, while empty/failed retries can retain stale artifacts.
- Treat the stage `finish_run` mismatch as proven: the helper accepts only `run_id`, `ok`, and `fail`, while stage keyword arguments are rejected and the resulting exception is suppressed.
- Treat lane-latest ownership as duplicated between each per-command wrapper and the outer shell exit trap.
- Preserve these defects for PR-A1 rather than silently repairing them in PR-A0.
- Confirm the embryo ordering remains valid; no plan amendment is needed.

## Acceptance evidence

- Commands:
  - `pytest -q tests/test_sensing_characterization.py`
  - `pytest -q tests/test_sensing_characterization.py tests/test_stage02_master_index_update.py tests/test_export_pr3a_buses.py tests/test_build_news_access_indexes.py`
  - `pytest -q`
- Tests:
  - 5 focused characterization tests passed.
  - 12 sensing/export/index tests passed in the combined targeted run.
- Runtime artifacts:
  - The failed-wrapper test executes an isolated child returning exit 7 and verifies its failed manifest, appended run record, captured partial stdout, latest lane status, and summary.
- Failure checks:
  - Child failure returns nonzero while leaving diagnostic telemetry.
  - `DRY_RUN=1` performs no acquisition fetch but still creates stage directories and attempts run-start bookkeeping.
  - Same-digest mirror replay replaces prior JSONL rather than appending.
- Known warnings:
  - The repository-wide test collection fails before tests run because legacy `tests/test_ids.py` and `tests/test_models.py` import a removed `backend` package. This pre-existing collection defect is outside sensing PR-A0; the targeted sensing suite passes.

## Deviations from embryo plan

none

## Remaining blockers

- Human approval of the PR-A0 writer/side-effect inventory is required before PR-A1 begins.
- The legacy repository-wide `backend` imports remain a general test-suite warning, but do not block the bounded PR-A1 sensing work.

## Next PR entry conditions

- A reviewer accepts the inventory classifications and characterization assertions.
- PR-A1 stays bounded to local bookkeeping, configuration, and side-effect separation.
- PR-A1 does not add AWS SDK, object storage, container, Terraform, or later immutable-bundle work.

## Exact re-entry command or first inspection

```bash
pytest -q tests/test_sensing_characterization.py && sed -n '1,260p' notes/media_monitor_aws_codex_retrofit_bundle_v0_1/docs/retrofit/aws_media_sensing/03_writer_side_effect_inventory_v0_1.md
```

Then read `prompts/PR-A1.md` before editing production code.

## Do not reopen

- The current sensing order is s01 → s02 → s03 → PR3a export → news access indexes.
- `DRY_RUN` currently couples s01 acquisition and enqueue behavior.
- The DB finish signature mismatch and broad suppression are proven current behavior.
- The per-command wrapper and outer shell are competing lane-latest writers.
- Shared append/overwrite files are not safe analogies for immutable S3 run evidence.

## Proposed carry-state update

- `current_pr`: `PR-A0`
- `status`: `REVIEW`
- `last_accepted_pr`: `null` (human review owns acceptance)
- `next_pr`: `PR-A1` (proposed; execute only after PR-A0 is accepted)
- `blockers`: `["Human approval of PR-A0 inventory and characterization evidence"]`
