from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "aws" / "sensing"


def test_terraform_packet_is_bounded_and_roles_are_separate() -> None:
    terraform = "\n".join(path.read_text(encoding="utf-8") for path in TF.glob("*.tf"))

    assert 'resource "aws_ecr_repository" "sensing"' in terraform
    assert 'resource "aws_ecs_cluster" "sensing"' in terraform
    assert 'resource "aws_ecs_task_definition" "sensing"' in terraform
    assert 'resource "aws_iam_role" "execution"' in terraform
    assert 'resource "aws_iam_role" "application"' in terraform
    assert "execution_role_arn" in terraform
    assert "task_role_arn" in terraform
    assert 'cpu                      = "256"' in terraform
    assert 'memory                   = "512"' in terraform
    assert 'retention_in_days = 14' in terraform
    assert "aws_s3_bucket_lifecycle_configuration" in terraform
    assert "aws_internet_gateway" in terraform
    assert "aws_nat_gateway" not in terraform
    assert "aws_db_instance" not in terraform
    assert "aws_scheduler" not in terraform
    assert "aws_cloudwatch_metric_alarm" not in terraform
    assert "aws_lambda" not in terraform


def test_application_role_is_confined_to_run_objects() -> None:
    iam = (TF / "iam.tf").read_text(encoding="utf-8")

    assert '"s3:GetObject"' in iam
    assert '"s3:PutObject"' in iam
    assert 'resources = ["${aws_s3_bucket.sensing.arn}/${var.s3_prefix}/runs/*"]' in iam
    assert "s3:ListBucket" not in iam
    assert "latest" not in iam
    assert "compacted" not in iam


def test_deployment_packet_contains_manual_proof_and_teardown_steps() -> None:
    deploy = (TF / "deploy.sh").read_text(encoding="utf-8")
    run = (TF / "run_first_task.sh").read_text(encoding="utf-8")
    teardown = (TF / "teardown.sh").read_text(encoding="utf-8")

    assert "docker build" in deploy and "docker push" in deploy
    assert "imageDigest" in deploy
    assert "terraform plan -out" in deploy
    assert "ecs run-task" in run and "ecs wait tasks-stopped" in run
    assert "iam_denial_confirmed" in run
    assert "/FINALIZED" in run
    assert "filter-log-events" in run
    assert "terraform" in teardown and "destroy" in teardown
    assert "CONFIRM_DESTROY" in teardown


def test_deployment_shell_scripts_parse() -> None:
    for script in ("deploy.sh", "run_first_task.sh", "teardown.sh"):
        subprocess.run(["bash", "-n", str(TF / script)], check=True)
