# Use module for service
module "algoitnyapi" {
  source = "../_module/algoitnyapi"

  # Name of service
  service_name = "algoitnyapi"

  # Port for service and healthcheck
  service_port     = 8000
  healthcheck_port = 8000

  # VPC Information via remote_state
  shard_id                 = data.terraform_remote_state.vpc.outputs.shard_id
  public_subnets           = data.terraform_remote_state.vpc.outputs.public_subnets
  private_subnets          = data.terraform_remote_state.vpc.outputs.private_subnets
  aws_region               = data.terraform_remote_state.vpc.outputs.aws_region
  vpc_cidr_numeral         = data.terraform_remote_state.vpc.outputs.cidr_numeral
  route53_internal_domain  = data.terraform_remote_state.vpc.outputs.route53_internal_domain
  route53_internal_zone_id = data.terraform_remote_state.vpc.outputs.route53_internal_zone_id
  target_vpc               = data.terraform_remote_state.vpc.outputs.vpc_id
  vpc_name                 = data.terraform_remote_state.vpc.outputs.vpc_name
  billing_tag              = data.terraform_remote_state.vpc.outputs.billing_tag

  # Domain Name 
  domain_name = "api"

  # Route53 variables
  acm_external_ssl_certificate_arn = var.r53_variables.prod.star_testcase_run_acm_arn_apnortheast2
  route53_external_zone_id         = var.r53_variables.prod.testcase_run_zone_id

  # Resource LoadBalancer variables
  lb_variables = var.lb_variables

  # Security Group variables
  sg_variables = var.sg_variables

  # CIDR for external LB
  # Control allowed IP for external LB 
  ext_lb_ingress_cidrs = [
    "0.0.0.0/0"
  ]
}
