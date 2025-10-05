# AWS kms Key
resource "aws_kms_key" "algoitny" {
  description         = "KMS key for common secrets in ${var.aws_region}."
  enable_key_rotation = true
}

# Alias for custom key
resource "aws_kms_alias" "algoitny_alias" {
  name          = "alias/algoitny"
  target_key_id = aws_kms_key.algoitny.key_id
}

