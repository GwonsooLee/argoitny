output "aws_security_group_ec2_id" {
  description = "ec2 instance security group"
  value       = aws_security_group.ec2.id
}

# External Load Balancer Outputs
output "external_lb_arn" {
  description = "ARN of external load balancer"
  value       = aws_lb.external.arn
}

output "external_lb_arn_suffix" {
  description = "ARN suffix of external load balancer for metrics"
  value       = aws_lb.external.arn_suffix
}

output "external_lb_dns_name" {
  description = "DNS name of external load balancer"
  value       = aws_lb.external.dns_name
}

output "external_lb_zone_id" {
  description = "Zone ID of external load balancer"
  value       = aws_lb.external.zone_id
}

output "external_lb_security_group_id" {
  description = "Security group ID of external load balancer"
  value       = aws_security_group.external_lb.id
}

# External Target Group Outputs
output "external_target_group_arn" {
  description = "ARN of external target group"
  value       = aws_lb_target_group.external.arn
}

output "external_target_group_arn_suffix" {
  description = "ARN suffix of external target group for metrics"
  value       = aws_lb_target_group.external.arn_suffix
}

output "external_target_group_name" {
  description = "Name of external target group"
  value       = aws_lb_target_group.external.name
}