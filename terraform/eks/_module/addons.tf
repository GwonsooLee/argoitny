# CoreDNS Addon
resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.eks_cluster.name

  addon_name    = "coredns"
  addon_version = var.coredns_version

  configuration_values = var.configuration_values

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    aws_eks_node_group.eks_node_group,
  ]

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-coredns",
  }))
}

# Kube-proxy Addon
resource "aws_eks_addon" "kube_proxy" {
  cluster_name  = aws_eks_cluster.eks_cluster.name
  addon_name    = "kube-proxy"
  addon_version = var.kube_proxy_version

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    aws_eks_node_group.eks_node_group,
  ]

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-kube-proxy",
  }))
}

# VPC CNI Addon
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.eks_cluster.name

  addon_name    = "vpc-cni"
  addon_version = var.vpc_cni_version

  service_account_role_arn    = aws_iam_role.cni_irsa_role.arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    aws_eks_node_group.eks_node_group,
  ]

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-vpc-cni",
  }))
}

# EBS CSI Driver Addon
resource "aws_eks_addon" "aws_ebs_csi_driver" {
  cluster_name = aws_eks_cluster.eks_cluster.name

  addon_name               = "aws-ebs-csi-driver"
  addon_version            = var.aws_ebs_csi_driver_version
  service_account_role_arn = aws_iam_role.ebs_csi_driver_irsa_role.arn

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    aws_eks_node_group.eks_node_group,
  ]

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-ebs-csi-driver",
  }))
}

# IAM Role for VPC CNI IRSA
resource "aws_iam_role" "cni_irsa_role" {
  name        = "eks-${var.cluster_name}-vpc-cni-irsa"
  description = "VPC CNI IRSA role for EKS cluster ${var.cluster_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.openid_connect_provider_id
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.openid_connect_provider_url}:sub" = "system:serviceaccount:kube-system:aws-node"
            "${local.openid_connect_provider_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-vpc-cni-irsa",
  }))
}

resource "aws_iam_role_policy_attachment" "cni_irsa_policy" {
  role       = aws_iam_role.cni_irsa_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

# IAM Role for EBS CSI Driver IRSA
resource "aws_iam_role" "ebs_csi_driver_irsa_role" {
  name        = "eks-${var.cluster_name}-ebs-csi-driver-irsa"
  description = "EBS CSI Driver IRSA role for EKS cluster ${var.cluster_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.openid_connect_provider_id
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.openid_connect_provider_url}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
            "${local.openid_connect_provider_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = merge(var.tags, tomap({
    "Name" = "eks-${var.cluster_name}-ebs-csi-driver-irsa",
  }))
}

resource "aws_iam_role_policy_attachment" "ebs_csi_driver_irsa_policy" {
  role       = aws_iam_role.ebs_csi_driver_irsa_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}
