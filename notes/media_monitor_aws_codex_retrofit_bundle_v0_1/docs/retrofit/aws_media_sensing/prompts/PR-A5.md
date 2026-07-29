# Codex Prompt — PR-A5: Minimal Terraform and first Fargate execution

Prerequisite: PR-A4 is accepted and AWS account inputs are available.

## Goal

Provision the minimum AWS resources and execute one manually triggered sensing task.

## Resources

- ECR;
- ECS cluster/task definition;
- task execution role;
- application task role;
- S3 bucket/prefix/lifecycle;
- CloudWatch log group;
- bounded network configuration;
- secrets/parameters only when needed.

## Acceptance

- clean plan/apply;
- image digest tied to commit;
- one remote task;
- immutable S3 run bundle;
- logs searchable by run ID;
- task role denied outside designated resources;
- teardown documented.

Normally defer EventBridge schedule and deployed compactor to A6.

Produce `context/closures/PR-A5.md` and propose `PR-A6`.
