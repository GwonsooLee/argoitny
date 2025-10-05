# Data source to read SOPS encrypted secret
data "sops_file" "secrets" {
  source_file = "${path.module}/secret.enc.yaml"
}

# AWS Secrets Manager Secret
resource "aws_secretsmanager_secret" "algoitny" {
  name                    = "algoitny/prod/apnortheast2"
  description             = "Algoitny production secrets for ap-northeast-2"
  recovery_window_in_days = 7

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
    Service     = "algoitny"
  }
}

# AWS Secrets Manager Secret Version
resource "aws_secretsmanager_secret_version" "algoitny" {
  secret_id     = aws_secretsmanager_secret.algoitny.id
  secret_string = jsonencode(data.sops_file.secrets.data)
}
