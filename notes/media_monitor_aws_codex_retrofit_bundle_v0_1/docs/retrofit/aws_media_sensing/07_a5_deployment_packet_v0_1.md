# PR-A5 Executable Deployment Packet v0.1

## Bounded resources

Terraform under `infra/aws/sensing` owns exactly:

- one immutable/scanned ECR repository with ten-image retention;
- one ECS cluster and one 0.25-vCPU/512-MiB Fargate task definition;
- separate ECS execution and sensing application roles;
- one encrypted, versioned, public-blocked S3 bucket with run/generation lifecycle;
- one 14-day CloudWatch log group;
- one VPC, internet gateway, two public subnets, route table, and no-ingress task
  security group with HTTPS and VPC-DNS egress;
- no secret because the bounded workload needs none.

It creates no schedule, alarm, Lambda, compactor task definition, NAT Gateway,
database, editorial/enrich resource, or site resource.

## Authority boundary

The task execution role uses only the AWS-managed ECS execution policy for image
pull and log delivery. The application role can only `GetObject`/`PutObject`
beneath `<bucket>/<prefix>/runs/*`; it cannot list the bucket or write
`compacted/*` or `latest/*`. The manual task enables a negative probe that must
receive `AccessDenied` when attempting a producer write under `latest/`.

## Executable sequence

1. Set `AWS_REGION`, optional `AWS_PROFILE`, and globally unique
   `SENSING_BUCKET_NAME`.
2. Run `infra/aws/sensing/deploy.sh`.
3. Set `DIGEST_AT` and run `infra/aws/sensing/run_first_task.sh`.
4. Retain generated task, S3, CloudWatch, and denial evidence beneath
   `artifacts/aws-a5/`.
5. Run the typed-confirmation teardown and retain its output.

The deployment bootstraps ECR only, builds/pushes or reuses the immutable
source-tagged image, resolves its registry digest, applies a saved full plan, and
requires a clean post-apply plan. The manual execution waits for task completion
and fails unless all four claims hold: exit zero, `FINALIZED` under the exact run
prefix, a correlated `bundle_uploaded` log, and an `iam_denial_confirmed` log.

## External block in this environment

Remote acceptance could not be executed because the environment exposes none of:

- AWS credentials/account identity;
- `AWS_REGION` or a globally unique bucket name;
- AWS CLI;
- Docker daemon/CLI.

Terraform itself was downloaded temporarily and the configuration validated
offline with the pinned AWS provider. Provider registry discovery is forbidden in
this environment, so validation used the official provider release mirror.

Smallest re-entry:

```bash
export AWS_REGION=<region>
export AWS_PROFILE=<profile>                 # omit when ambient credentials exist
export SENSING_BUCKET_NAME=<globally-unique-name>
aws sts get-caller-identity
docker version
infra/aws/sensing/deploy.sh
export DIGEST_AT=$(date -u +%Y%m%dT%H)
infra/aws/sensing/run_first_task.sh
```
