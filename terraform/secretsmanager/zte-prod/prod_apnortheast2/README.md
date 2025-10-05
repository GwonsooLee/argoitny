# Secrets Manager - Production (ap-northeast-2)

## Overview
This directory manages AWS Secrets Manager secrets for the algoitny production environment in ap-northeast-2 region using SOPS for encryption.

## Prerequisites
- SOPS installed: `brew install sops`
- AWS credentials configured with access to KMS key `alias/algoitny`
- Terraform >= 1.5.7

## Setup

### 1. Edit encrypted secrets
Edit the encrypted secrets directly using SOPS:

```bash
cd terraform/secretsmanager/zte-prod/prod_apnortheast2

# Edit encrypted file directly
sops secret.enc.yaml
```

This will decrypt the file in your editor, let you make changes, and re-encrypt it when you save.

### 2. Deploy with Terraform
```bash
# Initialize terraform
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply
```

## File Structure
- `.sops.yaml` - SOPS configuration
- `secret.enc.yaml` - SOPS encrypted secrets (committed to git)
- `algoitny.tf` - Secrets Manager resources
- `backend.tf` - Terraform backend configuration
- `provider.tf` - Provider configuration
- `variables.tf` - Input variables
- `outputs.tf` - Output values

## Security Notes
✅ Only `secret.enc.yaml` (encrypted file) is committed to git
🔑 KMS key `alias/algoitny` is used for encryption/decryption
⚠️ Edit secrets only via `sops secret.enc.yaml` command

## Accessing Secrets in AWS
```bash
# Get secret value
aws secretsmanager get-secret-value \
  --secret-id algoitny/prod/apnortheast2 \
  --region ap-northeast-2
```
