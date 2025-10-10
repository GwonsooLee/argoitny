# SQS Queues for AlgoItny
# Main queue for async job processing (problem generation, analysis, etc.)
# Dead Letter Queue (DLQ) for failed messages

# Dead Letter Queue
resource "aws_sqs_queue" "algoitny_dlq" {
  name                       = "${var.project_name}-dlq-${var.environment}"
  message_retention_seconds  = var.message_retention_seconds
  max_message_size          = var.max_message_size
  receive_wait_time_seconds = var.receive_wait_time_seconds

  # Server-side encryption
  sqs_managed_sse_enabled = true

  tags = merge(
    {
      Name        = "${var.project_name}-dlq-${var.environment}"
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Purpose     = "Dead Letter Queue for failed messages"
    },
    var.tags
  )
}

# Main Job Queue
resource "aws_sqs_queue" "algoitny_jobs" {
  name                       = "${var.project_name}-jobs-${var.environment}"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = var.message_retention_seconds
  max_message_size          = var.max_message_size
  delay_seconds             = var.delay_seconds
  receive_wait_time_seconds = var.receive_wait_time_seconds

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.algoitny_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

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

# CloudWatch Alarms for SQS monitoring

# Alarm for DLQ - Alert when messages are sent to DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-sqs-dlq-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when messages are sent to Dead Letter Queue"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.algoitny_dlq.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Alarm for Main Queue - Alert on high age of oldest message
resource "aws_cloudwatch_metric_alarm" "old_messages" {
  alarm_name          = "${var.project_name}-sqs-old-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 3600 # 1 hour
  alarm_description   = "Alert when messages are not being processed (age > 1 hour)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.algoitny_jobs.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Alarm for Main Queue - Alert on high queue depth
resource "aws_cloudwatch_metric_alarm" "high_queue_depth" {
  alarm_name          = "${var.project_name}-sqs-high-depth-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000
  alarm_description   = "Alert when queue depth is unusually high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.algoitny_jobs.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
