# AWS sensing substrate — PR-A5 deployment packet

This directory provisions only the manual sensing-task substrate: ECR, one ECS
cluster/task definition, separate execution/application roles, one versioned S3
bucket with lifecycle, a 14-day log group, and a two-subnet public VPC with no NAT
Gateway and no inbound task access. It does not create schedules, alarms, Lambda,
or deployed compaction.

## Required external inputs

- an AWS account and credentials allowed to manage the listed resources;
- `AWS_REGION` and optional `AWS_PROFILE`;
- a globally unique `SENSING_BUCKET_NAME`;
- local `terraform`, `aws`, `docker`, and `python` executables;
- outbound access to AWS APIs, ECR, and the public Python image/package registries.

No application secret is required. RSS acquisition uses public HTTPS sources.

## Deploy and prove the first task

```bash
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile                 # optional
export SENSING_BUCKET_NAME=globally-unique-name
infra/aws/sensing/deploy.sh

export DIGEST_AT=$(date -u +%Y%m%dT%H)
infra/aws/sensing/run_first_task.sh
```

`deploy.sh` bootstraps only ECR, builds/pushes `Dockerfile.sensing`, resolves its
immutable digest, writes an ignored deployment tfvars file, applies a saved full
plan, and requires a clean post-apply plan. `run_first_task.sh` waits for Fargate,
requires exit zero, verifies the immutable run prefix and `FINALIZED`, correlates
CloudWatch logs by run ID, and requires the producer's out-of-prefix write to have
failed with `AccessDenied`. Evidence is written beneath ignored `artifacts/aws-a5/`.

## Inspect

```bash
terraform -chdir=infra/aws/sensing output
aws s3api list-objects-v2 \
  --bucket "$(terraform -chdir=infra/aws/sensing output -raw bucket_name)" \
  --prefix "$(terraform -chdir=infra/aws/sensing output -raw s3_prefix)/runs/"
```

## Teardown

Teardown deliberately requires a typed confirmation. `allow_destroy=true` lets
Terraform empty the versioned evidence bucket and ECR repository as it destroys
them. Save the destroy output with the evidence packet.

```bash
CONFIRM_DESTROY=media-monitor-sensing infra/aws/sensing/teardown.sh \
  | tee artifacts/aws-a5/terraform-destroy.log
```
