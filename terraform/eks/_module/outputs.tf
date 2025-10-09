# EKS Cluster outputs
output "aws_eks_cluster_name" {
  description = "The name of the EKS cluster"
  value       = aws_eks_cluster.eks_cluster.name
}

output "aws_eks_cluster_id" {
  description = "The name/id of the EKS cluster"
  value       = aws_eks_cluster.eks_cluster.id
}

output "aws_eks_cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the cluster"
  value       = aws_eks_cluster.eks_cluster.arn
}

output "aws_eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.eks_cluster.endpoint
}

output "aws_eks_cluster_version" {
  description = "The Kubernetes version of the cluster"
  value       = aws_eks_cluster.eks_cluster.version
}

output "aws_eks_cluster_platform_version" {
  description = "The platform version for the cluster"
  value       = aws_eks_cluster.eks_cluster.platform_version
}

output "aws_eks_cluster_status" {
  description = "Status of the EKS cluster"
  value       = aws_eks_cluster.eks_cluster.status
}

output "aws_eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.eks_cluster.certificate_authority[0].data
  sensitive   = true
}

output "aws_eks_cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = try(aws_eks_cluster.eks_cluster.identity[0].oidc[0].issuer, "")
}

# Security Group outputs
output "aws_security_group_cluster_default_id" {
  description = "EKS cluster default security group"
  value       = aws_eks_cluster.eks_cluster.vpc_config[0].cluster_security_group_id
}

output "aws_security_group_cluster_id" {
  description = "EKS cluster security group"
  value       = aws_security_group.eks_cluster.id
}

# OIDC Provider outputs
output "aws_iam_openid_connect_provider_arn" {
  description = "IAM OpenId Connect Provider ARN for EKS"
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "aws_iam_openid_connect_provider_url" {
  description = "IAM OpenId Connect Provider URL for EKS"
  value       = aws_iam_openid_connect_provider.eks.url
}

# IAM Role outputs
output "aws_iam_role_cluster_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "aws_iam_role_cluster_name" {
  description = "Name of the EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.name
}

output "aws_iam_role_node_group_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = aws_iam_role.eks_node_group.arn
}

output "aws_iam_role_node_group_name" {
  description = "Name of the EKS node group IAM role"
  value       = aws_iam_role.eks_node_group.name
}
