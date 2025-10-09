locals {
  # Account Information
  account_id = var.account_id["prod"]  # Use "prod" key from var_global.tf

  # Cluster Information
  # Generate cluster name from shard_id and product with 4-character random suffix
  shard_id          = data.terraform_remote_state.vpc.outputs.shard_id
  base_cluster_name = "${local.shard_id}-${var.product}-eks"
  cluster_name      = "${local.base_cluster_name}-${random_string.cluster_suffix.result}"
  cluster_version   = var.cluster_version
  public_subnets    = data.terraform_remote_state.vpc.outputs.public_subnets
  private_subnets   = data.terraform_remote_state.vpc.outputs.private_subnets
  target_vpc        = data.terraform_remote_state.vpc.outputs.vpc_id

  # Addon version
  coredns_version            = var.coredns_version
  kube_proxy_version         = var.kube_proxy_version
  vpc_cni_version            = var.vpc_cni_version
  aws_ebs_csi_driver_version = var.aws_ebs_csi_driver_version

  # Managed Node Group inforation
  node_group_release_version = var.node_group_release_version

  # Fargate on EKS feature
  fargate_enabled      = var.fargate_enabled
  fargate_profile_name = var.fargate_enabled ? var.fargate_profile_name ? var.fargate_profile_name : "" : ""

  # access
  enable_public_access = var.enable_public_access
  additional_ingress   = var.additional_ingress

  # Cluster Access Roles
  # Please do not add the default roles or users here.
  aws_auth_master_users_arn = length(var.aws_auth_master_users_arn) > 0 ? var.aws_auth_master_users_arn : []
  aws_auth_master_roles_arn = length(var.aws_auth_master_roles_arn) > 0 ? var.aws_auth_master_roles_arn : []
  aws_auth_viewer_users_arn = length(var.aws_auth_viewer_users_arn) > 0 ? var.aws_auth_viewer_users_arn : []
  aws_auth_viewer_roles_arn = length(var.aws_auth_viewer_roles_arn) > 0 ? var.aws_auth_viewer_roles_arn : []

  assume_role_arn           = length(var.assume_role_arn) > 0 ? var.assume_role_arn : ""
  node_group_configurations = var.node_group_configurations != null && length(var.node_group_configurations) > 0 ? var.node_group_configurations : []

  common_tags = (tomap({
    "product"    = var.product,
    "account"    = var.account_alias,
    "shard_id"   = local.shard_id,
    "aws_region" = data.terraform_remote_state.vpc.outputs.aws_region
  }))

  tags = merge(var.tags, local.common_tags)

  configuration_values = jsonencode({
    "nodeSelector" : {
      "capacity_type" : "cpu_on_demand"
    },
  })
}
