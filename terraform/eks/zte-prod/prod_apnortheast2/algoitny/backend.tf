terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
    random = {
      source  = "hashicorp/random"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
    }
  }

  backend "s3" {
    bucket         = "zte-prod-apnortheast2-tfstate"
    key            = "terraform/eks/zte-prod/prod_apnortheast2/algoitny/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
