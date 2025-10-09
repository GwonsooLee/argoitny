# EKS Terraform Changelog

## [2025-01-10] - Latest Version Update

### Added
- **EKS 1.32 Support**: Updated to latest stable Kubernetes version (1.32)
- **Latest Add-on Versions**:
  - CoreDNS: v1.11.4-eksbuild.3
  - kube-proxy: v1.32.0-eksbuild.2
  - VPC CNI: v1.19.1-eksbuild.1
  - EBS CSI Driver: v1.38.0-eksbuild.1
- **IRSA for EBS CSI Driver**: Added proper IAM role for service accounts
- **CloudWatch Logging Control**: Made cluster logging optional via `enable_cluster_logging` variable
- **Cluster Access**: Both private and public endpoint access enabled for maximum flexibility
- **Random Cluster Suffix**: 4-character random suffix for cluster name uniqueness

### Improved
- **Modern Cluster Configuration**:
  - Access config with `API_AND_CONFIG_MAP` authentication mode
  - Upgrade policy with STANDARD support type
  - Bootstrap self-managed add-ons enabled
  - IP family explicitly set to ipv4
- **Add-on Management**:
  - Updated to use `resolve_conflicts_on_create` and `resolve_conflicts_on_update`
  - Added proper tags to all add-ons
  - Improved IRSA role definitions with aud condition
- **Node Groups**:
  - Enhanced lifecycle management with `create_before_destroy`
  - Updated to use AL2023 AMI type
  - Added SSM managed instance core policy
  - Improved update strategy with percentage-based unavailability

### Changed
- **Breaking**: Cluster now has both private and public access enabled by default
- **Breaking**: CloudWatch logging is now optional (defaults to disabled)
- Node group update config changed from absolute count to percentage
- Node group labels simplified (spot/on_demand instead of SPOT/CPU_ON_DEMAND)

### Fixed
- CloudWatch log group dependency issue
- IRSA role assume policy now includes aud condition
- Node group scaling config lifecycle ignores only desired_size

## Migration Guide

### From Previous Version

1. **Update terraform.tfvars**:
   ```hcl
   cluster_version = "1.32"
   coredns_version = "v1.11.4-eksbuild.3"
   kube_proxy_version = "v1.32.0-eksbuild.2"
   vpc_cni_version = "v1.19.1-eksbuild.1"
   aws_ebs_csi_driver_version = "v1.38.0-eksbuild.1"
   node_group_release_version = "1.32.0-20250109"
   
   # New variables
   enable_cluster_logging = true
   cluster_log_retention_days = 7
   ```

2. **Run Terraform**:
   ```bash
   terraform init -upgrade
   terraform plan
   terraform apply
   ```

3. **Verify**:
   ```bash
   aws eks describe-cluster --name <cluster-name> --region ap-northeast-2
   kubectl get nodes
   ```

## Version Matrix

| Component | Version |
|-----------|---------|
| EKS | 1.32 |
| CoreDNS | v1.11.4-eksbuild.3 |
| kube-proxy | v1.32.0-eksbuild.2 |
| VPC CNI | v1.19.1-eksbuild.1 |
| EBS CSI Driver | v1.38.0-eksbuild.1 |
| Node AMI | 1.32.0-20250109 (AL2023) |
| Terraform | >= 1.5.7 |
