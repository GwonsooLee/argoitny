# SQS Queue Outputs

# Main Job Queue Outputs
output "jobs_queue_id" {
  description = "ID of the main jobs queue"
  value       = aws_sqs_queue.algoitny_jobs.id
}

output "jobs_queue_arn" {
  description = "ARN of the main jobs queue"
  value       = aws_sqs_queue.algoitny_jobs.arn
}

output "jobs_queue_url" {
  description = "URL of the main jobs queue"
  value       = aws_sqs_queue.algoitny_jobs.url
}

output "jobs_queue_name" {
  description = "Name of the main jobs queue"
  value       = aws_sqs_queue.algoitny_jobs.name
}

# Dead Letter Queue Outputs
output "dlq_id" {
  description = "ID of the dead letter queue"
  value       = aws_sqs_queue.algoitny_dlq.id
}

output "dlq_arn" {
  description = "ARN of the dead letter queue"
  value       = aws_sqs_queue.algoitny_dlq.arn
}

output "dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.algoitny_dlq.url
}

output "dlq_name" {
  description = "Name of the dead letter queue"
  value       = aws_sqs_queue.algoitny_dlq.name
}

# CloudWatch Alarm Outputs
output "cloudwatch_alarm_dlq_messages_id" {
  description = "ID of the DLQ messages CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.dlq_messages.id
}

output "cloudwatch_alarm_old_messages_id" {
  description = "ID of the old messages CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.old_messages.id
}

output "cloudwatch_alarm_high_queue_depth_id" {
  description = "ID of the high queue depth CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.high_queue_depth.id
}
