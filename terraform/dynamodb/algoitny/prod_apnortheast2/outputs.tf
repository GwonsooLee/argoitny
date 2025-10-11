# DynamoDB Table Outputs

output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.algoitny_main.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.algoitny_main.arn
}

output "table_id" {
  description = "ID of the DynamoDB table"
  value       = aws_dynamodb_table.algoitny_main.id
}

output "table_stream_arn" {
  description = "ARN of the DynamoDB table stream"
  value       = aws_dynamodb_table.algoitny_main.stream_arn
}

output "table_stream_label" {
  description = "Label of the DynamoDB table stream"
  value       = aws_dynamodb_table.algoitny_main.stream_label
}

output "gsi1_name" {
  description = "Name of GSI1 (User Authentication Index)"
  value       = "GSI1"
}

output "gsi2_name" {
  description = "Name of GSI2 (Public History Timeline Index)"
  value       = "GSI2"
}

output "gsi3_name" {
  description = "Name of GSI3 (Problem Status Index)"
  value       = "GSI3"
}

output "cloudwatch_alarm_read_throttle_id" {
  description = "ID of the read throttle CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.read_throttle_events.id
}

output "cloudwatch_alarm_write_throttle_id" {
  description = "ID of the write throttle CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.write_throttle_events.id
}

# Django Table Outputs

output "django_table_name" {
  description = "Name of the Django/Celery DynamoDB table"
  value       = aws_dynamodb_table.algoitny_django.name
}

output "django_table_arn" {
  description = "ARN of the Django/Celery DynamoDB table"
  value       = aws_dynamodb_table.algoitny_django.arn
}

output "django_table_id" {
  description = "ID of the Django/Celery DynamoDB table"
  value       = aws_dynamodb_table.algoitny_django.id
}

output "django_table_stream_arn" {
  description = "ARN of the Django/Celery DynamoDB table stream"
  value       = aws_dynamodb_table.algoitny_django.stream_arn
}

output "django_table_stream_label" {
  description = "Label of the Django/Celery DynamoDB table stream"
  value       = aws_dynamodb_table.algoitny_django.stream_label
}

output "django_type_index_name" {
  description = "Name of TypeIndex GSI for Django table"
  value       = "TypeIndex"
}

output "django_cloudwatch_alarm_read_throttle_id" {
  description = "ID of the read throttle CloudWatch alarm for Django table"
  value       = aws_cloudwatch_metric_alarm.django_read_throttle_events.id
}

output "django_cloudwatch_alarm_write_throttle_id" {
  description = "ID of the write throttle CloudWatch alarm for Django table"
  value       = aws_cloudwatch_metric_alarm.django_write_throttle_events.id
}
