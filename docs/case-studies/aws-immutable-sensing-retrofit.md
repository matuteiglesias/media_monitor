# AWS immutable sensing retrofit

> **Status:** evidence-based case study · **Verified against:** `ec3765a` · **Maturity:** deployment-ready, not deployed or operated

## Problem and constraints

The local sensing lane wrote shared runtime/latest state. Moving that producer directly into concurrent cloud tasks would make retries overwrite evidence and give producers excessive authority. The retrofit had to preserve stage semantics, stable digest identity, local compatibility, public-feed access, low infrastructure complexity, and auditable failure evidence without introducing a scheduler or redesigning editorial lanes.

## Before and after

**Before:** stages 01–03/export/index ran against shared `data/` and `storage/`; success was largely process-oriented and latest state could conflate production with promotion.

**After:** each attempt runs in an isolated root and creates an immutable bundle containing inputs, outputs, stage records/logs, quarantine, candidates, checksums, manifest, and a final marker. In AWS, the producer uploads only its unique S3 run prefix. A separately authorized compactor validates bundles, deterministically selects one attempt per digest, writes an immutable generation, then alone updates `current.json`.

## Key decisions

- Physical run identity is unique while logical identity remains `sensing:<digest_at>`.
- `FINALIZED` is last and checksums, not exit zero, determine eligibility.
- Immutable-key retries are accepted only when bytes match.
- Generation identity derives from selected fingerprints/rejections; replay over identical evidence is stable.
- Producer and compactor IAM are distinct; the first-task proof requires producer out-of-prefix `AccessDenied`.
- Terraform provisions a manual Fargate substrate with immutable ECR digest, versioned S3, bounded logs, public egress/no inbound access, and typed teardown.

## Alternatives rejected

Direct producer writes to “latest,” timestamp-only selection, mutable image tags, process exit as evidence, broad shared IAM, and adding scheduling/alarms before the manual task boundary was proven were rejected because they weaken replay, provenance, or scope control.

## Evidence and failure model

Source: acquire run-bundle/compactor/S3 adapters, task adapters, `Dockerfile.sensing`, and `infra/aws/sensing/*.tf`/scripts. Focused tests cover characterization, finalization, corruption rejection, deterministic selection, concurrency/atomic pointer behavior, S3 actor separation/idempotency, container controls, and Terraform packet invariants. The deployment runbook requires independent ECR/ECS/S3/log/IAM reconciliation and teardown evidence.

## Honest outcome

The repository demonstrates implemented and locally validated code plus a deployment-ready packet. It contains no provider evidence proving resources were deployed, tasks repeatedly operated, recovery exercised in AWS, scheduling, alarms, or deployed compaction. See the [architecture decision](../architecture/decisions/0001-immutable-runs-single-writer-state.md) and [operational runbook](../operations/aws-sensing-deployment.md).
