output "ecr_repository_url" {
  value = aws_ecr_repository.sensing.repository_url
}

output "bucket_name" {
  value = aws_s3_bucket.sensing.id
}

output "s3_prefix" {
  value = var.s3_prefix
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.sensing.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.sensing.arn
}

output "task_role_arn" {
  value = aws_iam_role.application.arn
}

output "execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "subnet_ids" {
  value = aws_subnet.public[*].id
}

output "security_group_id" {
  value = aws_security_group.task.id
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.sensing.name
}
