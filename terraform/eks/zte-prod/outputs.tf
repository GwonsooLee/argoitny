# Regional outputs
output "prod_apnortheast2_algoitny_cluster_id" {
  description = "The name/id of the AlgoItny EKS cluster in ap-northeast-2"
  value       = try(module.prod_apnortheast2.algoitny_cluster_id, null)
}

output "prod_apnortheast2_algoitny_cluster_endpoint" {
  description = "Endpoint for AlgoItny EKS control plane in ap-northeast-2"
  value       = try(module.prod_apnortheast2.algoitny_cluster_endpoint, null)
}

output "prod_apnortheast2_algoitny_oidc_provider_arn" {
  description = "ARN of the OIDC Provider for AlgoItny EKS in ap-northeast-2"
  value       = try(module.prod_apnortheast2.algoitny_oidc_provider_arn, null)
}
