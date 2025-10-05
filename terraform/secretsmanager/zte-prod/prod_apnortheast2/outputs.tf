output "aws_secretsmanager_secret_prod_apne2_algoitny_arn" {
  description = "ARN of algoitny secrets"
  value       = aws_secretsmanager_secret.algoitny.arn
}

output "aws_secretsmanager_secret_prod_apne2_algoitny_name" {
  description = "Name of algoitny secrets"
  value       = aws_secretsmanager_secret.algoitny.name
}
