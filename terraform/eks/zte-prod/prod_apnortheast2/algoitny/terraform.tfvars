# Basic Information
account_alias = "zte-prod"
product       = "algoitny"

# Cluster information
# Latest stable EKS version as of January 2025
cluster_version = "1.32"

# Addon information
# https://docs.aws.amazon.com/ko_kr/eks/latest/userguide/managing-coredns.html
coredns_version            = "v1.11.4-eksbuild.3"

# https://docs.aws.amazon.com/ko_kr/eks/latest/userguide/managing-kube-proxy.html
kube_proxy_version         = "v1.32.0-eksbuild.2"

# https://docs.aws.amazon.com/ko_kr/eks/latest/userguide/managing-vpc-cni.html
vpc_cni_version            = "v1.19.1-eksbuild.1"

# https://github.com/kubernetes-sigs/aws-ebs-csi-driver
aws_ebs_csi_driver_version = "v1.38.0-eksbuild.1"

# Managed Node Group inforation
# https://github.com/awslabs/amazon-eks-ami/releases
node_group_release_version = "1.32.0-20250109"

# Fargate Information
fargate_enabled      = false
fargate_profile_name = ""

# access
# Note: Both private and public access are enabled by default for flexibility
enable_public_access = true
additional_ingress   = []

# CloudWatch logging
enable_cluster_logging     = true
cluster_log_retention_days = 7

# Node Group configuration
# NOTE: This cluster uses Karpenter for node management.
# No managed node groups are configured here.
# Karpenter will dynamically provision nodes based on pod requirements.
node_group_configurations = []

# Cluster Access
aws_auth_master_roles_arn = []

aws_auth_master_users_arn = [
  "arn:aws:iam::YOUR_ACCOUNT_ID:user/admin"
]

aws_auth_viewer_roles_arn = []

aws_auth_viewer_users_arn = []
