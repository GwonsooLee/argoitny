data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = {
    bucket = "zte-prod-apnortheast2-tfstate"
    key    = "terraform/vpc/zte_apnortheast2/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
