resource "aws_s3_bucket" "sensing" {
  bucket        = var.bucket_name
  force_destroy = var.allow_destroy
}

resource "aws_s3_bucket_public_access_block" "sensing" {
  bucket = aws_s3_bucket.sensing.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sensing" {
  bucket = aws_s3_bucket.sensing.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "sensing" {
  bucket = aws_s3_bucket.sensing.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "sensing" {
  bucket = aws_s3_bucket.sensing.id

  depends_on = [aws_s3_bucket_versioning.sensing]

  rule {
    id     = "expire-immutable-runs"
    status = "Enabled"
    filter {
      prefix = "${var.s3_prefix}/runs/"
    }
    expiration {
      days = 30
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  rule {
    id     = "expire-old-compacted-generations"
    status = "Enabled"
    filter {
      prefix = "${var.s3_prefix}/compacted/"
    }
    expiration {
      days = 90
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

data "aws_iam_policy_document" "secure_transport" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.sensing.arn,
      "${aws_s3_bucket.sensing.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "secure_transport" {
  bucket = aws_s3_bucket.sensing.id
  policy = data.aws_iam_policy_document.secure_transport.json
}
