terraform {
  required_version = ">= 1.5.7"

  backend "s3" {
    bucket         = "zte-prod-apnortheast2-tfstate"
    key            = "terraform/kms/zte-prod/prod_apnortheast2/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
