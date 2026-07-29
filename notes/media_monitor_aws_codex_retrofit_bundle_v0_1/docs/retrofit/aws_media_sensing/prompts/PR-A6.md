# Codex Prompt — PR-A6: Schedule, compact, alarm, fail, recover, and package evidence

Prerequisite: PR-A5 is accepted.

## Goal

Operate sensing unattended with one governed state writer and demonstrate failure/recovery.

## Scope

- EventBridge Scheduler for ECS sensing task;
- scheduled Lambda or bounded ECS compactor;
- single-writer enforcement;
- task-state and application failure visibility;
- stale/failed sensing alarm;
- multiple executions;
- cost/security/teardown review;
- machine-readable acceptance pack.

## Failure probes

- invalid feed config;
- network/source failure;
- S3 write denial;
- duplicate/replayed run;
- out-of-order compaction.

OpenTelemetry is prunable. Failure/recovery is not.

Produce `context/closures/PR-A6.md`. Activate A7 only with a real consumer decision; otherwise close.
