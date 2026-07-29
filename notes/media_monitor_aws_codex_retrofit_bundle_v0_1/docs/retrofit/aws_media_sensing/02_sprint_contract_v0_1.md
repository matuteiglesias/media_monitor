# AWS Media Monitor Sensing Sprint Contract v0.1

**Status:** FROZEN, IMPLEMENT ONLY AFTER GCP SPRINT IS VALIDATED OR PARKED  
**Host repository:** `matuteiglesias/media_monitor`  
**Workload:** Sensing lane only  
**Estimated implementation:** 8 deep-focus blocks, approximately 24–30 hours  
**Learning focus:** turn a locally stateful pipeline into an immutable-run system with one explicit state owner.

---

## 1. Claim to be earned

After acceptance, the honest portfolio claim is:

> Deployed and operated the Media Monitor sensing lane as an hourly ECS/Fargate task using ECR, EventBridge Scheduler, S3, least-authority IAM roles, CloudWatch, Lambda, and Terraform. Each digest runs in an isolated workspace, publishes immutable contract and run evidence, and is promoted by one deterministic state compactor. A controlled mid-run failure was ignored by the compactor, retried safely, and recovered without corrupting latest state.

This claim excludes editorial generation, enrichment, PromptFlow, the public site, high-volume streaming, and production newsroom operation.

---

## 2. Bounded workload

One Fargate task executes exactly:

```text
s01 acquisition
  → s02 current digest mapping / master candidate
  → s03 grouped digest
  → export-pr3a
  → build-news-access-indexes
  → validate
  → package immutable run
```

The workload includes:

- public RSS acquisition;
- deterministic digest identity;
- current-digest validation and quarantine;
- `news_ref.v1` and `news_digest_group.v1`;
- candidate recent-news indexes;
- run manifest and checksums;
- candidate cumulative `master_ref` state.

The workload excludes:

- scrape queue writes;
- Postgres run bookkeeping;
- editorial lane;
- enrich lane;
- PromptFlow;
- draft/publish flows;
- Vercel deployment.

### Runtime limits

- one task per scheduled digest;
- 0.25 vCPU;
- 0.5–1 GiB memory;
- 15-minute hard timeout;
- maximum two attempts;
- one logical digest per task;
- no overlapping accepted state promotions.

---

## 3. Architecture decision

### Decision: immutable run artifacts plus one scheduled state compactor

Do not let Fargate tasks write shared `latest` objects or canonical mutable state.

Each task writes only to:

```text
s3://<bucket>/media-monitor/sensing/runs/<digest_at>/<run_id>/...
```

A separate Lambda compactor is the sole writer of:

```text
state/master_ref.csv
indexes/news_recent_refs_latest.jsonl
indexes/news_recent_groups_latest.jsonl
status/sensing_latest.json
status/summary.json
```

The compactor runs on its own EventBridge schedule approximately 15–20 minutes after the sensing task. It recomputes latest state from immutable completed manifests.

Why scheduled compaction for v0.1:

- S3 event notifications are at-least-once and may arrive later than expected;
- an event-triggered writer would need duplicate and ordering defenses immediately;
- a small deterministic scheduled compactor is easier to reason about and replay;
- one reserved-concurrency Lambda makes state ownership visible.

The compactor must still be idempotent because EventBridge Scheduler and Lambda may retry.

---

## 4. Current code findings that define Gate 0

### 4.1 Run bookkeeping is not trustworthy yet

The current `db.finish_run` helper accepts:

```python
finish_run(run_id, ok, fail)
```

but sensing stages call it with additional `stage` and `meta` keyword arguments and suppress exceptions.

Result: a stage can print success while its DB run finalization silently failed.

Decision:

- remove Postgres run bookkeeping from the cloud sensing path;
- replace it with one explicit run manifest;
- fix or deprecate the mismatched local calls separately.

### 4.2 Network acquisition and queue side effects are coupled

Stage 01 uses `DRY_RUN` both to control network acquisition and to skip scrape enqueue.

Decision:

Introduce separate controls:

```text
ACQUIRE_NETWORK=1
ENQUEUE_SCRAPE=0
DB_RUN_BOOKKEEPING=0
```

The AWS sensing task acquires feeds but never enqueues scrape work.

### 4.3 Feed configuration is embedded in code

The RSS map is currently hardcoded.

Decision:

Move the feed set into one versioned configuration file shipped in the image:

```text
config/sensing_feeds.v1.yaml
```

Its checksum is recorded in each run manifest.

No dynamic user-supplied URLs in v0.1.

### 4.4 Mutable local state has multiple writers

Current code writes or overwrites:

- `data/master_ref.csv`;
- `storage/indexes/pr3a_exports_latest.json`;
- `storage/indexes/pr3a_export_compact_latest.json`;
- `storage/indexes/news_recent_*_latest.jsonl`;
- lane latest and summary JSON;
- stage/wrapper status surfaces.

Decision:

- task-local writes are allowed only inside an isolated work directory;
- all task outputs become immutable candidate artifacts;
- only the compactor promotes accepted candidates.

### 4.5 Lane status currently has competing writers

The stage wrapper writes lane status after stages, and the outer shell trap also writes a lane latest status.

Decision:

One orchestration owner emits the authoritative sensing run manifest. Child stages return structured stage results; they do not own lane latest state.

---

## 5. Architecture

```text
EventBridge Scheduler (:00)
        │
        ▼
ECS/Fargate sensing task
        │
        ├── isolated /work/<run_id>
        ├── fetch feeds
        ├── run s01/s02/s03
        ├── export contracts
        ├── build candidate indexes
        ├── validate + checksum
        ├── upload immutable run prefix
        └── write final completion manifest last
                │
                ▼
              S3

EventBridge Scheduler (:20)
        │
        ▼
Lambda state compactor
        │
        ├── list recent completed manifests
        ├── validate checksums and digest order
        ├── select newest acceptable run
        ├── promote candidate master/indexes
        └── write latest health/status
                │
                ├── S3 canonical state
                └── CloudWatch metrics/alarms
```

ECS uses separate task execution and task roles: the execution role permits the ECS/Fargate agent to pull the image and send logs; the application task role grants the container its narrow S3/config access.

### 5.1 Task identity

```text
logical_run_id = sensing:<digest_at>
attempt_id     = UUID or scheduler invocation identity
run_id         = <logical_run_id>:attempt:<n>
```

Two attempts may share one logical digest but never one immutable S3 prefix.

### 5.2 Isolated workspace

```text
/work/<run_id>/
  data/
  storage/
  evidence/
```

All existing local-path code runs against this directory.

At start, the task may download:

```text
state/master_ref.csv
```

plus its metadata manifest.

If canonical state is missing, the task begins from an empty master.

If canonical state is older than the allowed staleness threshold, the task fails closed rather than silently building from stale state.

### 5.3 S3 layout

```text
media-monitor/sensing/
  runs/YYYY/MM/DD/<digest_at>/<run_id>/
    input/feed_config.yaml
    input/feed_config.sha256
    raw/rss_slices/
    intermediate/digest_map/
    intermediate/digest_jsonls/
    contracts/news_ref.v1.jsonl
    contracts/news_digest_group.v1.jsonl
    candidates/master_ref.csv
    candidates/news_recent_refs.jsonl
    candidates/news_recent_groups.jsonl
    quarantine/
    stage_results.jsonl
    run_manifest.json
    COMPLETE
  state/
    master_ref.csv
    master_ref.manifest.json
  indexes/
    news_recent_refs_latest.jsonl
    news_recent_groups_latest.jsonl
  status/
    sensing_latest.json
    summary.json
```

`COMPLETE` or the finalized manifest is uploaded last. The compactor ignores prefixes without a valid completion marker.

### 5.4 Run manifest

Required fields:

```text
schema_version
logical_run_id
run_id
attempt
digest_at
source_commit
image_digest
feed_config_sha256
started_at
completed_at
status
stage_results
input_state_digest
output_artifacts[]
checksums
counts
quarantine_count
failure_code
```

Contractual statuses:

- `success`;
- `partial_success`;
- `empty_success`;
- `error`.

### 5.5 State compactor

The compactor:

1. lists completed manifests in a bounded recent prefix;
2. validates manifest and artifact checksums;
3. ignores incomplete/error runs;
4. orders candidates by:
   - `digest_at`;
   - `completed_at`;
   - `run_id`;
5. rejects a candidate based on state older than the currently promoted state;
6. copies/promotes the selected candidate state and indexes;
7. writes one latest status summary;
8. emits metrics.

Set Lambda reserved concurrency to 1.

The compactor is replayable for a requested time window.

### 5.6 Observability

CloudWatch Logs:

- structured JSON;
- `run_id`, `logical_run_id`, `digest_at`, `stage`, `status`, `error_code`;
- one log group for sensing task;
- one for compactor.

Metrics:

- task success/failure;
- accepted digest age;
- news reference count;
- digest group count;
- quarantine count;
- compactor rejection count;
- last successful promotion age.

Alarms:

- no accepted digest for more than two cadence windows;
- two consecutive task failures;
- compactor failure;
- unexpectedly zero outputs for repeated runs.

---

## 6. Gates

### Gate 0 — Local sensing contract

Pass when:

- DB bookkeeping mismatch is characterized and no longer silently affects cloud status;
- acquisition and enqueue controls are separated;
- feed configuration is externalized and versioned;
- one orchestration owner emits the run manifest;
- a fixture run is deterministic;
- all outputs fit under one isolated root.

### Gate 1 — Immutable-run refactor

Pass when:

- each run writes a unique directory;
- no stage writes canonical latest state;
- final completion marker is written last;
- failed/incomplete runs remain inspectable;
- rerunning the same digest with a new attempt cannot overwrite prior evidence.

### Gate 2 — State compactor

Pass when:

- compactor selects the correct newest successful run;
- duplicate invocation is idempotent;
- out-of-order completion does not regress state;
- incomplete and checksum-invalid runs are ignored;
- master and latest indexes are promoted together or not at all.

### Gate 3 — Container and local image run

Pass when:

- one image runs the sensing command from a clean environment;
- filesystem writes remain under `/work`;
- the image contains no `.env` or credentials;
- dependency installation is pinned;
- image runs as non-root;
- local container evidence matches fixture expectations.

### Gate 4 — Terraform and IAM

Pass when Terraform provisions:

- ECR repository;
- ECS cluster/task definition;
- EventBridge sensing schedule;
- S3 bucket and lifecycle;
- CloudWatch logs, metrics, and alarms;
- task execution role;
- task role;
- scheduler execution role;
- compactor Lambda and role;
- compactor schedule;
- budget alert.

No console-only resource is required.

### Gate 5 — Manual AWS execution

Pass when:

- a manually started Fargate task completes;
- all immutable artifacts are present;
- CloudWatch logs reconcile with the manifest;
- compactor promotes the run;
- `sensing_latest.json` references the correct run;
- the task has no permission outside its S3 prefix.

### Gate 6 — Failure and recovery

Pass when the controlled probe succeeds.

### Gate 7 — Operated evidence

Pass when:

- at least six scheduled sensing tasks run;
- at least three are accepted by the compactor;
- one controlled failure and recovery is present;
- freshness alarm behavior is demonstrated;
- resource cost remains within the boundary;
- the evidence packet is independently understandable.

---

## 7. Failure probe

Use:

```text
FAILPOINT=after_candidate_upload_before_complete
```

First attempt:

1. runs all stages;
2. uploads candidate artifacts;
3. exits nonzero before final completion marker.

Expected:

- immutable partial evidence remains;
- compactor ignores the run;
- canonical state and latest indexes do not change;
- task failure appears in CloudWatch;
- scheduler/ECS retry or a controlled second attempt begins.

Second attempt:

- succeeds for the same `digest_at`;
- writes a different attempt prefix;
- finalizes `COMPLETE`;
- compactor promotes exactly that attempt;
- no duplicate accepted state exists;
- previous failed artifacts remain available for diagnosis.

Additional domain probe:

- include one intentionally invalid feed URL in a test feed configuration;
- require bounded quarantine/partial-success behavior;
- do not allow one bad source to corrupt valid outputs.

---

## 8. Evidence

Required evidence:

- sensing architecture decision record;
- local state-writer inventory;
- local deterministic fixture;
- run-manifest schema;
- compactor tests for duplicate/out-of-order/incomplete runs;
- Docker image digest and source commit;
- Terraform plan;
- IAM role/policy inventory;
- ECS task definition revision;
- EventBridge schedules;
- successful task ARN;
- CloudWatch log query by `run_id`;
- S3 immutable run tree;
- checksum validation report;
- compactor promotion record;
- denied S3 access probe;
- failure attempt and recovery attempt;
- alarm test;
- cost estimate and actual billing snapshot;
- teardown command;
- concise public case-study summary.

---

## 9. Cost boundary

Hard limits:

- one AWS account/environment for the sprint;
- one ECR repository;
- one ECS cluster;
- one Fargate task per hour only after acceptance;
- 0.25 vCPU;
- maximum 1 GiB memory;
- 15-minute timeout;
- maximum two attempts;
- one S3 bucket;
- one small compactor Lambda;
- no NAT Gateway;
- no RDS/Aurora;
- no EKS;
- no Step Functions;
- CloudWatch log retention: 14 days;
- raw/intermediate S3 lifecycle: 30 days;
- selected manifests/contracts may be retained longer;
- budget alert at **$10/month**.

Pause the schedules if forecast spend exceeds the boundary.

---

## 10. Exclusions

- editorial lane;
- enrich lane;
- PromptFlow;
- OpenAI/model calls;
- scrape queue;
- Postgres/RDS;
- Vercel/public-site deployment;
- article publication;
- S3-event-driven compaction in v0.1;
- Lambda acquisition pipeline;
- Kubernetes/EKS;
- API Gateway;
- streaming/Kinesis;
- multi-region availability;
- automatic migration of historical local artifacts;
- redesign of content/editorial contracts;
- a separate repository split during the sprint.

---

## 11. Stop condition

Stop and mark the sprint `PARKED` when:

1. sensing cannot run without editorial or enrich;
2. Postgres becomes mandatory for the bounded workload;
3. task-local writes cannot be confined to an isolated root;
4. canonical state still has more than one writer;
5. the compactor cannot reject incomplete or out-of-order runs;
6. retries duplicate or regress state;
7. current local behavior cannot be pinned by fixtures;
8. the sprint exceeds 30 focused hours without one accepted manual Fargate run;
9. RDS, Step Functions, EKS, or another large service is proposed to avoid a small code refactor.

The stop artifact records the failed gate and smallest re-entry condition.

---

## 12. Deep-focus implementation plan

### Block 1 — Trace the real sensing state machine

**Goal:** inventory every read, write, and side effect.

Work:

- trace s01–s03, export, indexes, wrappers;
- classify artifacts as input, intermediate, contract, candidate state, latest state, or telemetry;
- pin current failure behavior;
- document duplicate writers.

Learning checkpoint:

> Which files describe facts from one run, and which claim to describe the system now?

Exit: complete writer/owner map.

### Block 2 — Fix the local orchestration contract

**Goal:** one owner and one truthful result.

Work:

- separate network, enqueue, and DB flags;
- remove cloud dependence on DB bookkeeping;
- create stage-result contract;
- create one run manifest;
- add deterministic fixture and failure cases.

Exit: Gate 0.

### Block 3 — Isolate every run

**Goal:** make concurrency safe before introducing concurrency.

Work:

- parameterize data/storage roots;
- unique work directory;
- candidate artifact names;
- completion marker last;
- non-overwrite tests.

Exit: Gate 1.

### Block 4 — Build the compactor locally

**Goal:** define canonical state as a deterministic function of immutable runs.

Work:

- manifest discovery;
- validation/checksums;
- ordering;
- candidate promotion;
- stale-state rejection;
- replay command;
- tests for duplicate, incomplete, and out-of-order runs.

Exit: Gate 2.

### Block 5 — Containerize the sensing runtime

**Goal:** reproduce one full run from a clean image.

Work:

- pinned dependencies;
- non-root user;
- feed config;
- entrypoint;
- resource bounds;
- local image run;
- evidence comparison.

Exit: Gate 3.

### Block 6 — Provision the AWS substrate

**Goal:** create the smallest production-shaped environment.

Work:

- ECR/ECS/Fargate;
- S3/lifecycle;
- execution role versus task role;
- schedules disabled by default;
- Lambda compactor;
- logs/metrics/alarms;
- budget.

Exit: Gate 4.

### Block 7 — Execute, fail, recover

**Goal:** prove state safety.

Work:

- manual task;
- compactor promotion;
- denied-access test;
- failpoint before completion;
- retry;
- verify no latest-state mutation from failed attempt;
- verify exactly one accepted recovery.

Exit: Gate 5 and Gate 6.

### Block 8 — Operate and externalize

**Goal:** earn the claim without widening scope.

Work:

- enable hourly schedule;
- collect accepted runs;
- test freshness alarm;
- record spend;
- package evidence;
- document teardown;
- decide whether local legacy writers should be retired.

Retirement forecast:

- mark Postgres run bookkeeping as local/legacy for sensing if no active consumer remains;
- keep editorial/enrich ownership inside `media_monitor`;
- build a narrow sensing image context;
- extract a separate repository only after a second deployment consumer or incompatible release lifecycle exists.

Exit: Gate 7 and sprint closure.
