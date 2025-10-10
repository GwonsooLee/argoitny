# SQS Queue for AlgoItny
# Main queue for async job processing (problem generation, analysis, etc.)

# Main Job Queue
resource "aws_sqs_queue" "algoitny_jobs" {
  name                       = "${var.project_name}-jobs-${var.environment}"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = var.message_retention_seconds
  max_message_size          = var.max_message_size
  delay_seconds             = var.delay_seconds
  receive_wait_time_seconds = var.receive_wait_time_seconds

  # Server-side encryption
  sqs_managed_sse_enabled = true

  tags = merge(
    {
      Name        = "${var.project_name}-jobs-${var.environment}"
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Purpose     = "Main queue for async job processing"
    },
    var.tags
  )
}
