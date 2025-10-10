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
