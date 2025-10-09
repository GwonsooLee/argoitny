# Outputs from algoitny cluster
output "algoitny_cluster_id" {
  description = "The name/id of the AlgoItny EKS cluster"
  value       = try(module.algoitny.cluster_id, null)
}

output "algoitny_cluster_base_name" {
  description = "The base name of the AlgoItny EKS cluster (without random suffix)"
  value       = try(module.algoitny.cluster_base_name, null)
}

output "algoitny_cluster_suffix" {
  description = "The random 4-character suffix for the cluster name"
  value       = try(module.algoitny.cluster_suffix, null)
}

output "algoitny_cluster_endpoint" {
  description = "Endpoint for AlgoItny EKS control plane"
  value       = try(module.algoitny.cluster_endpoint, null)
}

output "algoitny_cluster_oidc_issuer_url" {
  description = "The URL on the AlgoItny EKS cluster OIDC Issuer"
  value       = try(module.algoitny.cluster_oidc_issuer_url, null)
}

output "algoitny_oidc_provider_arn" {
  description = "ARN of the OIDC Provider for AlgoItny EKS"
  value       = try(module.algoitny.oidc_provider_arn, null)
}
