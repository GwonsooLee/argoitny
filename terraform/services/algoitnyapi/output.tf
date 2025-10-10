output "aws_security_group_ec2_id" {
  description = "algoitnyapi name node security group"
  value       = module.algoitnyapi.aws_security_group_ec2_id
}

output "external_lb_security_group_id" {
  description = "Security group ID of external load balancer"
  value       = module.algoitnyapi.external_lb_security_group_id
}

output "external_target_group_arn" {
  description = "ARN of external target group"
  value       = module.algoitnyapi.external_target_group_arn
}

output "external_target_group_arn_suffix" {
  description = "ARN suffix of external target group for metrics"
  value       = module.algoitnyapi.external_target_group_arn_suffix
}

output "external_lb_arn_suffix" {
  description = "ARN suffix of external load balancer for metrics"
  value       = module.algoitnyapi.external_lb_arn_suffix
}
