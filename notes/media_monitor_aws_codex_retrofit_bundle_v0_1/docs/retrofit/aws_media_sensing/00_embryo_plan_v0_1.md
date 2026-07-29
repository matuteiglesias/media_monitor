# AWS Media Monitor Sensing Retrofit — Embryo Plan v0.1

## North

Operate only the Media Monitor sensing lane as a scheduled AWS workload while preserving its existing contracts, stable identities, failure isolation, and human/editorial boundaries.

The cloud retrofit must make a new claim honest:

> The sensing lane runs independently on ECS/Fargate under least-authority roles, writes immutable per-run evidence to S3, exposes task and application failure in CloudWatch, and supports safe retry and recovery without migrating editorial, enrich, or publication.

## Architectural decisions already frozen

1. **Sensing only.** Editorial, PromptFlow, enrich, and Vercel publication remain outside the sprint.
2. **Immutable run objects.** A Fargate task does not append to shared S3 JSONL files or race to overwrite `latest.json`.
3. **One governed compactor.** Cumulative master/index/latest state is produced by a separately invoked single-writer compactor.
4. **Scheduled compaction first.** Do not begin with S3 event fan-out; object notifications are at-least-once and immediately create ordering/duplicate complexity.
5. **Task execution role and application task role are separate.**
6. **Current local/systemd runtime remains a compatibility adapter until the AWS path is accepted.**

## Product ownership

| Concern | Owner |
|---|---|
| RSS acquisition and digest windows | `news_acquire` sensing domain |
| Stable article/digest identities | existing sensing code/contracts |
| Export bus/index semantics | Media Monitor |
| Run evidence shape | Media Monitor producer-side run contract |
| Per-run cloud execution | ECS/Fargate adapter |
| Immutable run storage | S3 adapter |
| Latest/cumulative state | single-writer compactor |
| Task lifecycle telemetry | ECS/EventBridge/CloudWatch |
| Editorial and publication | existing non-AWS surfaces |

## Phase map

```text
Phase 0 — Characterize mutation, side effects, and current defects
      ↓
Phase 1 — Repair local sensing semantics and configuration
      ↓
Phase 2 — Isolate one immutable sensing run bundle
      ↓
Phase 3 — Build deterministic single-writer compactor
      ↓
Phase 4 — Add S3 adapters and cloud-safe task entrypoint
      ↓
Phase 5 — Provision ECS/Fargate and first remote task
      ↓
Phase 6 — Schedule, alarm, fail, recover, package evidence
```

## Critical chain and pruning

| PR | Purpose | Dependency | Classification | Can be pruned? |
|---|---|---|---|---|
| `PR-A0` | Install embryo plan and characterize current writers/side effects | none | Fundamental | No |
| `PR-A1` | Repair run bookkeeping and separate acquisition/enqueue/config semantics | A0 accepted | Critical | No |
| `PR-A2` | Per-run working root and immutable sensing bundle | A1 accepted | Critical | No |
| `PR-A3` | Deterministic single-writer compactor | A2 accepted | Critical | No |
| `PR-A4` | S3 adapters, container, cloud entrypoint, task-safe telemetry | A3 accepted | Critical | No |
| `PR-A5` | Terraform for ECR/ECS/IAM/S3/CloudWatch; first task | A4 accepted | Critical for cloud claim | No |
| `PR-A6` | EventBridge schedule, alarms, failure/recovery, evidence | A5 accepted | Critical for `OPERATED` | OTel may be pruned; failure/recovery may not |
| `PR-A7` | Optional publication/consumer handoff or component extraction | A6 accepted | Optional | Yes |

## Phase 0 — Characterize before repair

### PR-A0 — Retrofit control surface and mutation inventory

**Goal**

Add this plan and pin the present sensing behavior through tests and an explicit writer/side-effect inventory.

**Must characterize**

- canonical sensing entrypoint and stage order;
- environment knobs;
- network fetch behavior;
- optional Postgres run/enqueue behavior;
- all files written by s01–s03, export, index, wrappers, and outer status handlers;
- append versus atomic replace versus overwrite;
- run-record/status ownership;
- repeated same-`DIGEST_AT` behavior;
- DB bookkeeping API compatibility;
- failure suppression.

**No behavior fixes in this PR.**

## Phase 1 — Repair local sensing semantics

### PR-A1 — Bookkeeping, configuration, and side-effect separation

**Goal**

Make the local sensing product coherent before introducing cloud storage.

**Expected scope**

- correct and test run-start/run-finish bookkeeping contracts;
- stop swallowing errors that invalidate run evidence;
- separate these knobs:
  - fetch network sources;
  - write acquisition artifacts;
  - enqueue scrape jobs;
  - write optional DB bookkeeping;
- externalize feed configuration under an explicit schema;
- establish one producer-side owner for run records/status;
- preserve current local golden path through compatibility defaults.

**Non-goals**

- no AWS SDK;
- no object storage;
- no editorial/enrich changes.

## Phase 2 — Isolate immutable sensing execution

### PR-A2 — Per-run working root and run bundle

**Goal**

Make one sensing execution self-contained and replayable.

**Design**

```text
run_id / digest_at
   ├── inputs/config snapshot
   ├── stage outputs
   ├── exported buses
   ├── compact access candidates
   ├── run record
   ├── manifest/checksums
   └── exception/failure evidence
```

No task-owned mutable `latest` output belongs in the bundle.

**Acceptance**

- a configurable run root;
- same digest/run replay behavior defined;
- partial failure still yields a valid failed/partial bundle;
- local compatibility promotion is separate from production;
- existing stable IDs and schema validation remain intact.

## Phase 3 — Single-writer state

### PR-A3 — Deterministic compactor

**Goal**

Build a pure or near-pure compactor that consumes immutable run bundles and produces cumulative/latest state.

**Owned outputs may include**

- canonical master reference;
- compact recent refs/groups indexes;
- lane latest/status summary;
- accepted run pointer.

**Required semantics**

- deterministic ordering;
- duplicate run/object tolerance;
- out-of-order bundle tolerance;
- atomic local publication;
- one writer;
- no editorial/enrich ownership.

This PR is fundamental because S3 does not support safe shared append semantics.

## Phase 4 — AWS adapters

### PR-A4 — S3 layout, container, task entrypoint

**Goal**

Implement the AWS storage and task seams before provisioning infrastructure.

**S3 layout**

```text
s3://<bucket>/<prefix>/
  runs/<run_id>/...
  accepted/<run_id>.json
  compacted/<generation>/...
  latest/<named pointer>.json   # compactor only
```

**Task behavior**

- writes only under its run prefix;
- emits structured stdout/stderr;
- uses task role for S3 and optional secrets;
- makes optional Postgres behavior explicit;
- does not invoke editorial or site publication;
- exits non-zero on contract failure.

**Acceptance**

- local container execution;
- S3 adapter contract tests/fakes;
- no shared mutable writer in sensing task;
- source commit/image/run linkage;
- task-safe timeout/resource assumptions.

## Phase 5 — Minimal AWS infrastructure

### PR-A5 — Terraform and first Fargate task

**Resources**

- ECR;
- ECS cluster/task definition;
- task execution role;
- application task role;
- S3 bucket/prefix and lifecycle;
- CloudWatch log group;
- network configuration;
- secrets/parameters only when required.

EventBridge schedule and Lambda compactor may be deferred to A6 if needed.

**Acceptance**

- clean plan/apply;
- image digest tied to commit;
- one remote sensing task;
- immutable S3 bundle;
- CloudWatch logs correlated by run ID;
- denied access to unrelated S3 prefixes/resources;
- teardown documented.

## Phase 6 — Operate and close

### PR-A6 — Scheduler, compactor deployment, alarms, failure/recovery

**Goal**

Demonstrate that the sensing lane can operate unattended and recover safely.

**Infrastructure**

- EventBridge Scheduler → ECS task;
- separately scheduled Lambda or bounded ECS compactor;
- reserved concurrency/single-writer enforcement;
- task-state and application failure visibility;
- alarm for failed/missed/stale sensing.

**Failure probes**

- malformed/empty feed configuration;
- network/source failure;
- S3 write denial;
- duplicate/replayed run bundle;
- compactor receiving out-of-order bundles.

**Acceptance**

- multiple executions;
- one visible failure;
- alarm or operational signal;
- safe rerun/recovery;
- no duplicate/corrupted latest state;
- cost/security review;
- evidence pack and honest maturity label.

## Optional Phase 7 — Consumer or extraction

### PR-A7 — Optional accepted-run handoff

Only activate when an existing consumer needs the cloud-produced compacted state.

Possible consumers:

- current local editorial lane;
- current publication build;
- a provider-neutral evidence catalog.

Do not migrate those systems merely to complete the diagram.

## Retirement and extraction policy

### Keep in `media_monitor` initially

- sensing domain;
- run-bundle contract;
- compactor;
- AWS adapters;
- Terraform;
- runbooks/evidence.

### Compatibility surfaces

- local/systemd entrypoints;
- local filesystem storage;
- local Postgres behavior when explicitly enabled.

### Candidates for retirement after AWS acceptance

- duplicate lane-latest writers;
- silent best-effort bookkeeping that contradicts run status;
- shared append/overwrite patterns used as runtime truth;
- heartbeat paths that duplicate managed scheduling evidence.

### Extraction gate

Extract the compactor or run-evidence package only when:

1. another producer uses the same immutable-bundle semantics;
2. it needs an independent release/security lifecycle;
3. remaining in `media_monitor` creates real dependency pressure.

## Stop conditions

Stop when:

- A6 is accepted and the AWS claim is honest; or
- a reproducible external blocker is documented; or
- A2/A3 reveal that stable product semantics cannot be separated from mutable local state without a larger redesign.

Do not expand into EKS, Step Functions, Bedrock, a site migration, or a general event platform.
