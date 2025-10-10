# API Server Outputs
output "api_server_asg_name" {
  description = "Name of the API server Auto Scaling Group"
  value       = aws_autoscaling_group.api_server.name
}

output "api_server_asg_arn" {
  description = "ARN of the API server Auto Scaling Group"
  value       = aws_autoscaling_group.api_server.arn
}

output "api_server_launch_template_id" {
  description = "ID of the API server launch template"
  value       = aws_launch_template.api_server.id
}

output "api_server_security_group_id" {
  description = "Security group ID for API servers"
  value       = aws_security_group.api_server.id
}

output "api_server_iam_role_arn" {
  description = "IAM role ARN for API servers"
  value       = aws_iam_role.api_server.arn
}

# Worker Outputs
output "worker_asg_name" {
  description = "Name of the Worker Auto Scaling Group"
  value       = aws_autoscaling_group.worker.name
}

output "worker_asg_arn" {
  description = "ARN of the Worker Auto Scaling Group"
  value       = aws_autoscaling_group.worker.arn
}

output "worker_launch_template_id" {
  description = "ID of the Worker launch template"
  value       = aws_launch_template.worker.id
}

output "worker_security_group_id" {
  description = "Security group ID for Workers"
  value       = aws_security_group.worker.id
}

output "worker_iam_role_arn" {
  description = "IAM role ARN for Workers"
  value       = aws_iam_role.worker.arn
}
