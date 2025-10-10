data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = var.remote_state.vpc.zteapne2
}
