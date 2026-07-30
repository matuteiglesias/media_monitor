# AWS sensing deployment and first task

> **Status:** canonical deployment-ready runbook; not deployed/operated evidence · **Owner:** AWS sensing infrastructure/operator · **Verified against:** `e068f5a`

## Preflight

Use an authorized disposable/known AWS account. Install `terraform`, `aws`, `docker`, `python`; authenticate; set `AWS_REGION`, optional `AWS_PROFILE`, and globally unique `SENSING_BUCKET_NAME`. Review the saved plan, cost, public-subnet/no-inbound design, versioned bucket retention, and teardown impact.

## Deploy and prove

```bash
export AWS_REGION=us-east-1
export SENSING_BUCKET_NAME=globally-unique-name
infra/aws/sensing/deploy.sh | tee artifacts/aws-a5/deploy.log
export DIGEST_AT=YYYYMMDDTHH
infra/aws/sensing/run_first_task.sh | tee artifacts/aws-a5/first-task.log
```

These provider-mutating commands are **unverified in this environment**. The scripts require an immutable ECR digest, saved full plan, clean post-apply plan, task exit zero, finalized S3 run, correlated CloudWatch logs, and a successful `AccessDenied` producer out-of-prefix probe.

## Independent verification

Capture Terraform outputs/clean plan, ECR digest/source commit, ECS task ARN/status/exit, S3 manifest/checksums/`FINALIZED`, CloudWatch run-ID logs, and denial probe. Do not claim deployment from local tests or apply output alone. The packet has no schedule, alarms, Lambda, or deployed compactor.

## Failure/retry/teardown

Use a new run ID/attempt; never overwrite a run prefix. Stop on mutable image tags, non-clean plan, missing finalization, checksum mismatch, or denial-probe success. Teardown is destructive and typed:

```bash
CONFIRM_DESTROY=media-monitor-sensing infra/aws/sensing/teardown.sh | tee artifacts/aws-a5/terraform-destroy.log
```

Preserve evidence before teardown and independently confirm declared resources are gone; versioned S3/ECR deletion is enabled only by the teardown path.
