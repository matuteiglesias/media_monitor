variable "aws_region" {
  description = "AWS region for the bounded sensing environment."
  type        = string
}

variable "environment" {
  description = "Short environment label."
  type        = string
  default     = "sprint"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name supplied by the operator."
  type        = string
}

variable "image_uri" {
  description = "Immutable ECR image URI in repository@sha256:digest form."
  type        = string

  validation {
    condition     = can(regex("^[^@]+@sha256:[0-9a-f]{64}$", var.image_uri))
    error_message = "image_uri must use immutable repository@sha256:<64 hex> form."
  }
}

variable "source_commit" {
  description = "Full source commit embedded in run manifests."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_commit))
    error_message = "source_commit must be a full 40-character Git SHA."
  }
}

variable "s3_prefix" {
  description = "Provider-neutral sensing key prefix."
  type        = string
  default     = "media-monitor/sensing"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "allow_destroy" {
  description = "Set only during explicit teardown to permit deletion of evidence and images."
  type        = bool
  default     = false
}
