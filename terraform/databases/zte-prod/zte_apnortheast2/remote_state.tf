data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = merge(
    {
      bucket = var.remote_state.vpc.zteapne2.bucket
      key    = var.remote_state.vpc.zteapne2.key
      region = var.remote_state.vpc.zteapne2.region
    },
    var.assume_role_arn != "" ? {
      assume_role = {
        role_arn = var.assume_role_arn
      }
    } : {}
  )
}
