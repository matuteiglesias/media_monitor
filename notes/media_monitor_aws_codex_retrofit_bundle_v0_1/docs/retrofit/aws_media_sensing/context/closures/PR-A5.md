# PR Closure Note

## Identity

- Retrofit: `aws_media_sensing`
- PR: `PR-A5`
- Status: `BLOCKED_EXTERNAL`
- Base commit: `dcb3f8d`
- Head commit: this PR's review commit
- Date: 2026-07-29

## Goal accepted

Produced a validated, bounded, executable Terraform/deployment packet for the first manual Fargate sensing task. Remote execution is conclusively blocked by absent AWS account inputs, AWS CLI, and Docker rather than missing repository implementation.

## Files and surfaces changed

- Bounded Terraform for ECR, ECS/Fargate, execution/application IAM, S3 security/lifecycle, CloudWatch Logs, and public no-NAT networking.
- Deployment, manual-run/evidence, and typed-confirmation teardown scripts.
- Producer IAM denial probe with structured evidence.
- A5 deployment packet/runbook and static Terraform packet tests.
- No scheduler, alarm, deployed compactor, secret, editorial/enrich, or site surface.

## Invariants preserved

- The sensing producer writes only immutable run objects and `FINALIZED` last.
- The application role cannot list the bucket or write compacted/latest prefixes.
- The execution role is distinct and owns image-pull/log-delivery authority.
- Image URI is digest-addressed and source commit/image digest remain task inputs.
- No schedule or A6 resource is provisioned.

## Decisions made

- Use two public subnets with task public IPs and no NAT Gateway; no inbound rule exists.
- Limit task size to 0.25 vCPU and 512 MiB with the application-enforced 15-minute timeout.
- Use no secret because public RSS plus task-role S3 access requires none.
- Retain logs for 14 days, immutable run objects for 30 days, compacted generations for 90 days, and ten ECR images.
- Require an in-task negative IAM probe against `latest/`; unexpected success fails the task.
- Outcome is `BLOCKED_EXTERNAL`, not an unsubstantiated remote success claim.

## Acceptance evidence

- Commands:
  - `terraform fmt -recursive -check infra/aws/sensing`
  - `terraform -chdir=infra/aws/sensing init -backend=false` using an official local provider mirror
  - `terraform -chdir=infra/aws/sensing validate`
  - `AWS_EC2_METADATA_DISABLED=true terraform -chdir=infra/aws/sensing plan ...` (expected external failure: `No valid credential sources found`)
  - `pytest -q tests/test_sensing_terraform_packet.py tests/test_sensing_container_task.py tests/test_sensing_s3_store.py`
  - `bash -n infra/aws/sensing/deploy.sh infra/aws/sensing/run_first_task.sh infra/aws/sensing/teardown.sh`
  - `git diff --check`
- Tests:
  - Terraform resource boundary, separate roles, application policy confinement, no NAT/scheduler/alarm/Lambda, proof steps, and teardown guard.
  - Structured IAM denial event behavior.
- Runtime artifacts:
  - Valid Terraform configuration and complete commands for image digest, apply, task execution, S3 evidence, CloudWatch correlation, denial proof, and destroy.
- Failure checks:
  - Missing commands/inputs fail deployment before mutation.
  - Task fails if the forbidden producer write unexpectedly succeeds.
  - Manual evidence verification fails unless marker, correlated upload, and denial log are all present.
- Known warnings:
  - No AWS plan/apply, Docker build/push, Fargate task, S3 object, CloudWatch event, remote denial, billing, or teardown was claimed because required provider inputs are absent.
  - Terraform registry discovery is forbidden here; validation used the official provider release archive and pinned lock data.

## Deviations from embryo plan

The intended remote acceptance could not run. The embryo stop rule permits a reproducible external blocker with the smallest re-entry condition; this PR supplies the complete deployment packet instead of fabricating evidence.

## Remaining blockers

- AWS credentials/account with permission to create the bounded resources.
- `AWS_REGION` and globally unique `SENSING_BUCKET_NAME`.
- AWS CLI and Docker daemon/CLI.

## Next PR entry conditions

- Do not enter PR-A6.
- Resume PR-A5 with the exact external inputs, execute deploy/manual task/teardown, and attach generated evidence.
- Only after human acceptance of real remote evidence may carry advance to PR-A6.

## Exact re-entry command or first inspection

```bash
export AWS_REGION=<region> AWS_PROFILE=<profile> SENSING_BUCKET_NAME=<unique-name>
aws sts get-caller-identity && docker version
infra/aws/sensing/deploy.sh
export DIGEST_AT=$(date -u +%Y%m%dT%H)
infra/aws/sensing/run_first_task.sh
```

## Do not reopen

- Resource boundary and no-NAT public networking design.
- Separate execution/application roles and producer run-prefix policy.
- No application secret is required.
- Scheduling, alarms, and deployed compaction remain A6.

## Proposed carry-state update

- `current_pr`: `PR-A5`
- `status`: `BLOCKED_EXTERNAL`
- `last_accepted_pr`: `PR-A4`
- `next_pr`: `PR-A5`
- `blockers`: `["AWS credentials/account", "AWS region and unique bucket", "AWS CLI", "Docker daemon/CLI"]`
