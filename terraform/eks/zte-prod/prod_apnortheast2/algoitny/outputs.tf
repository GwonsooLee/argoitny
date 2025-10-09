# EKS Cluster outputs
output "cluster_id" {
  description = "The name/id of the EKS cluster (includes random suffix)"
  value       = module.eks.aws_eks_cluster_name
}

output "cluster_base_name" {
  description = "The base name of the EKS cluster (without random suffix)"
  value       = local.base_cluster_name
}

output "cluster_suffix" {
  description = "The random 4-character suffix for the cluster name"
  value       = random_string.cluster_suffix.result
}

output "cluster_arn" {
  description = "The Amazon Resource Name (ARN) of the cluster"
  value       = module.eks.aws_eks_cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.aws_eks_cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.aws_security_group_cluster_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.aws_eks_cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.aws_iam_openid_connect_provider_url
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for EKS"
  value       = module.eks.aws_iam_openid_connect_provider_arn
}
