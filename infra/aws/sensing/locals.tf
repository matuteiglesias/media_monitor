locals {
  name         = "media-monitor-sensing-${var.environment}"
  image_digest = split("@", var.image_uri)[1]
  tags = {
    Project     = "media-monitor"
    Component   = "sensing"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
