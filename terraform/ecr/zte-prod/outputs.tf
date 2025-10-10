output "algoitny_repository_url" {
  description = "URL of the AlgoItny ECR repository"
  value       = aws_ecr_repository.algoitny.repository_url
}

output "algoitny_repository_arn" {
  description = "ARN of the AlgoItny ECR repository"
  value       = aws_ecr_repository.algoitny.arn
}

output "algoitny_repository_name" {
  description = "Name of the AlgoItny ECR repository"
  value       = aws_ecr_repository.algoitny.name
}
