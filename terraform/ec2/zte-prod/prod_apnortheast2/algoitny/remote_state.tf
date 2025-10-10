# Remote state for VPC
data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = {
    bucket = "zte-apne2-tfstate"
    key    = "terraform/vpc/zte_apnortheast2/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

# Remote state for ECR
data "terraform_remote_state" "ecr" {
  backend = "s3"

  config = {
    bucket = "zte-apne2-tfstate"
    key    = "terraform/ecr/zte-prod/prod_apnortheast2/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

# Remote state for Databases (ElastiCache Redis)
data "terraform_remote_state" "databases" {
  backend = "s3"

  config = {
    bucket = "zte-apne2-tfstate"
    key    = "terraform/databases/zte-prod/zte_apnortheast2/algoitny/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

# Remote state for Services (ALB, Target Groups)
data "terraform_remote_state" "services" {
  backend = "s3"

  config = {
    bucket = "zte-apne2-tfstate"
    key    = "terraform/services/algoitnyapi/zte_apnortheast2/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
