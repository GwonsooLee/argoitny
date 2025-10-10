terraform {
  backend "s3" {
    bucket         = "zte-prod-apnortheast2-tfstate"
    key            = "terraform/ec2/zte-prod/prod_apnortheast2/algoitny/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
