resource "aws_ecr_repository" "sensing" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = var.allow_destroy

  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "sensing" {
  repository = aws_ecr_repository.sensing.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain the ten newest sensing images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "sensing" {
  name              = "/ecs/${local.name}"
  retention_in_days = 14
}

resource "aws_ecs_cluster" "sensing" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "sensing" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.application.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "sensing"
    image     = var.image_uri
    essential = true
    environment = [
      { name = "SENSING_S3_BUCKET", value = aws_s3_bucket.sensing.id },
      { name = "SENSING_S3_PREFIX", value = var.s3_prefix },
      { name = "SOURCE_COMMIT", value = var.source_commit },
      { name = "IMAGE_DIGEST", value = local.image_digest },
      { name = "ACQUIRE_NETWORK", value = "1" },
      { name = "ENQUEUE_SCRAPE", value = "0" },
      { name = "DB_RUN_BOOKKEEPING", value = "0" },
      { name = "SENSING_TASK_TIMEOUT_SECONDS", value = "900" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.sensing.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "task"
      }
    }
  }])
}
