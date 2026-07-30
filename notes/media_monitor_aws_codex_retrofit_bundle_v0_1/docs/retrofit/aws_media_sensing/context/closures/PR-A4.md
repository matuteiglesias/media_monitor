# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A4`
- Status: `ACCEPTED`
- Base commit: `4171ce2`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Added AWS-facing storage and task seams, a sensing-only non-root container, structured task telemetry, explicit runtime limits, and source/image/run linkage without provisioning infrastructure.

## Files and surfaces changed

- `s3_store.py`: key layout, producer/compactor authority separation, immutable retry semantics, run download, generation upload, and latest-pointer publication.
- `run_sensing_task.py`: bounded cloud producer entrypoint and structured events.
- `run_sensing_compactor_task.py`: adapter entrypoint around unchanged compactor semantics.
- `Dockerfile.sensing`, `.dockerignore`, and exact sensing dependency pins.
- Bundle manifest now records `image_digest` and accepts deployment-provided source identity.
- AWS task/storage contract and focused fake-S3/container/task tests.

## Invariants preserved

- The producer writes only its immutable run prefix and uploads `FINALIZED` last.
- Only the compactor writes compacted generations and the mutable latest pointer.
- Compactor ordering, replay, and cumulative merge semantics are unchanged.
- No shared JSONL append exists.
- Editorial, enrich, site, and publication are absent from the task/image path.

## Decisions made

- Adapter actor identity is explicit and enforced before SDK calls.
- Immutable S3 puts use `If-None-Match: *`; identical retries succeed by byte comparison and conflicting retries fail.
- The compactor uploads a complete immutable generation before replacing `latest/current.json`.
- Task execution requires `SOURCE_COMMIT` and `IMAGE_DIGEST`; missing linkage is a contract failure.
- Task timeout is bounded to 900 seconds. Intended 0.25 vCPU, 0.5–1 GiB, and at most two attempts are documented for PR-A5 enforcement.
- App and execution role expectations are separate and documented, but not provisioned here.

## Acceptance evidence

- Commands:
  - `pytest -q tests/test_sensing_s3_store.py tests/test_sensing_container_task.py tests/test_sensing_run_bundle.py tests/test_sensing_compactor.py`
  - `python -m compileall -q apps/news_acquire/src/news_acquire scripts/run_sensing_task.py scripts/run_sensing_compactor_task.py`
  - `git diff --check`
- Tests:
  - Producer prefix confinement, immutable retry, completion-marker ordering, and denied compactor operations.
  - Compactor discovery/download, immutable generation upload, and latest-pointer-last behavior.
  - Unsafe run identity rejection.
  - Narrow non-root Docker copy surface, secret exclusions, exact dependency pins, and structured configuration failure.
- Runtime artifacts:
  - Fake S3 objects exercise the complete adapter request shape without AWS credentials.
- Failure checks:
  - Conflicting bytes at an immutable key fail.
  - Actor authority violations fail before storage access.
  - Missing task configuration emits structured JSON and exits non-zero without traceback noise.
- Known warnings:
  - Docker is unavailable in this environment, so the Dockerfile is inspected programmatically but not built locally.
  - No real AWS calls are made; remote execution and denied-access evidence belong to PR-A5.
  - Repository-wide legacy `backend` import collection failures remain outside this PR.

## Deviations from embryo plan

none

## Remaining blockers

- Human approval of S3 layout, role expectations, and container boundary.
- Image build/digest and first remote task require PR-A5 infrastructure.

## Next PR entry conditions

- PR-A4 is accepted.
- Storage layout and task environment contract are frozen for Terraform.
- PR-A5 provisions only the minimal ECR/ECS/IAM/S3/CloudWatch substrate and first task.

## Exact re-entry command or first inspection

```bash
pytest -q tests/test_sensing_s3_store.py tests/test_sensing_container_task.py && cat notes/media_monitor_aws_codex_retrofit_bundle_v0_1/docs/retrofit/aws_media_sensing/prompts/PR-A5.md
```

## Do not reopen

- Producer and compactor write prefixes are disjoint.
- `FINALIZED` is the producer completion object and uploads last.
- Compactor `latest/current.json` uploads only after its generation.
- The sensing image contains no editorial/enrich/site or credentials.

## Proposed carry-state update

- `current_pr`: `PR-A4`
- `status`: `REVIEW`
- `last_accepted_pr`: `PR-A3`
- `next_pr`: `PR-A5` after human acceptance; retain `PR-A4` while under review
- `blockers`: `["Human approval of PR-A4 storage, task, and container contracts"]`
