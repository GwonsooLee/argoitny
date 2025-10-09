# AlgoItny EKS Terraform Configuration

This directory contains Terraform configurations for AlgoItny EKS clusters in the zte-prod AWS account.

## Directory Structure

```
zte-prod/
├── prod_apnortheast2/          # ap-northeast-2 region
│   ├── algoitny/               # AlgoItny EKS cluster
│   │   ├── backend.tf          # Terraform backend configuration
│   │   ├── cluster.tf          # EKS cluster module configuration
│   │   ├── locals.tf           # Local variables
│   │   ├── outputs.tf          # Cluster outputs
│   │   ├── provider.tf         # AWS provider configuration
│   │   ├── remote_state.tf     # Remote state data sources (VPC)
│   │   ├── terraform.tfvars    # Cluster-specific variables
│   │   ├── var_global.tf       # Global variables (symlink)
│   │   └── variables.tf        # Variable definitions
│   ├── algoitny.tf             # Module reference
│   ├── backend.tf              # Regional backend
│   ├── outputs.tf              # Regional outputs
│   └── provider.tf             # Regional provider
├── outputs.tf                  # Account-level outputs
├── prod_apnortheast2.tf        # Regional module reference
├── provider.tf                 # Account-level provider
└── variables.tf                # Account-level variables
```

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform >= 1.5.7** installed
3. **S3 backend bucket** already created: `zte-prod-apnortheast2-tfstate`
4. **DynamoDB table** for state locking: `terraform-lock`
5. **VPC** already deployed (referenced via remote state)

## Configuration

### Cluster Configuration

Edit `prod_apnortheast2/algoitny/terraform.tfvars` to customize:

- **Cluster Version**: EKS version (currently 1.31)
- **Addon Versions**: CoreDNS, kube-proxy, VPC CNI, EBS CSI driver
- **Node Groups**: Configure on-demand and spot instances
- **Access Control**: IAM users/roles for cluster access

### Node Groups

Two node groups are configured:

1. **algoitny-ondemand**
   - Instance Type: t3.medium
   - Capacity: 2-5 nodes
   - Purpose: Stable backend workloads
   - Labels: workload=backend, capacity_type=on_demand

2. **algoitny-spot**
   - Instance Types: t3.medium, t3a.medium
   - Capacity: 1-10 nodes
   - Purpose: Cost-effective worker nodes
   - Labels: workload=worker, capacity_type=spot

## Deployment

### Initialize Terraform

```bash
cd prod_apnortheast2/algoitny
terraform init
```

### Plan Changes

```bash
terraform plan
```

### Apply Changes

```bash
terraform apply
```

### Verify Deployment

```bash
# Get cluster outputs
terraform output

# Configure kubectl
aws eks update-kubeconfig --region ap-northeast-2 --name <cluster-name>

# Verify nodes
kubectl get nodes
```

## Outputs

After deployment, the following outputs are available:

- `cluster_id`: EKS cluster name
- `cluster_endpoint`: Kubernetes API server endpoint
- `cluster_oidc_issuer_url`: OIDC issuer URL for IRSA
- `oidc_provider_arn`: ARN of OIDC provider (for IAM roles)
- `cluster_security_group_id`: Cluster security group ID
- `cluster_certificate_authority_data`: CA certificate (sensitive)

## IAM Roles for Service Accounts (IRSA)

The cluster is configured with an OIDC provider. To create IAM roles for Kubernetes service accounts:

```hcl
data "aws_iam_openid_connect_provider" "eks" {
  url = module.algoitny.cluster_oidc_issuer_url
}

resource "aws_iam_role" "service_account_role" {
  name = "algoitny-backend-sa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(data.aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:default:algoitny-backend-sa"
        }
      }
    }]
  })
}
```

## Required IAM Policies

The service account role should have the following policies:

1. **DynamoDB Access**
   - `dynamodb:*` on AlgoItny tables

2. **SQS Access**
   - `sqs:*` on Celery queues

3. **S3 Access**
   - `s3:*` on testcase bucket (`algoitny-testcases-zteapne2`)

4. **Secrets Manager Access**
   - `secretsmanager:GetSecretValue` on `algoitny-secrets`

## Access Configuration

Update `terraform.tfvars` to grant cluster access:

```hcl
aws_auth_master_users_arn = [
  "arn:aws:iam::YOUR_ACCOUNT_ID:user/admin"
]
```

## Upgrading

### Upgrade Kubernetes Version

1. Update `cluster_version` in `terraform.tfvars`
2. Run `terraform plan` to preview changes
3. Apply with `terraform apply`
4. Update node groups (may require replacement)

### Upgrade Addons

Update addon versions in `terraform.tfvars`:
- `coredns_version`
- `kube_proxy_version`
- `vpc_cni_version`
- `aws_ebs_csi_driver_version`

Refer to AWS documentation for compatible versions.

## Troubleshooting

### Cannot Connect to Cluster

```bash
# Update kubeconfig
aws eks update-kubeconfig --region ap-northeast-2 --name <cluster-name>

# Verify IAM permissions
aws sts get-caller-identity
```

### Nodes Not Joining

Check:
1. Node IAM role permissions
2. Security group rules
3. Subnet configuration (must have internet access)

### State Lock Issues

```bash
# List locks
aws dynamodb scan --table-name terraform-lock

# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

## Maintenance

### View Resources

```bash
terraform state list
```

### Import Existing Resources

```bash
terraform import <resource_type>.<resource_name> <resource_id>
```

### Destroy Cluster

**WARNING**: This will delete all resources!

```bash
terraform destroy
```

## Related Resources

- VPC: `terraform/vpc/zte_apnortheast2/`
- DynamoDB: `terraform/dynamodb/algoitny/prod_apnortheast2/`
- S3: `terraform/s3/zte-prod/prod_apnortheast2/`
- Secrets Manager: `terraform/secretsmanager/zte-prod/prod_apnortheast2/`

## Support

For issues or questions, contact the infrastructure team.

## Karpenter Setup

This EKS cluster is configured to use Karpenter for node provisioning instead of managed node groups.

### Why Karpenter?

- **Dynamic Provisioning**: Automatically provisions nodes based on pod requirements
- **Cost Optimization**: Uses spot instances efficiently and right-sizes nodes
- **Faster Scaling**: Provisions nodes in seconds vs minutes with cluster autoscaler
- **Better Bin Packing**: Optimizes pod placement for better resource utilization

### Prerequisites

After the cluster is created, you'll need to:

1. **Install Karpenter** (via Helm or Terraform)
2. **Create NodePools** to define node provisioning rules
3. **Configure EC2NodeClass** for instance requirements

### Example Karpenter NodePool

```yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: kubernetes.io/os
          operator: In
          values: ["linux"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["t3", "t3a", "t4g"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["small", "medium", "large"]
      nodeClassRef:
        name: default
  limits:
    cpu: 100
    memory: 100Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 720h # 30 days
---
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023
  role: "KarpenterNodeRole-${CLUSTER_NAME}"
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "${CLUSTER_NAME}"
  userData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh "${CLUSTER_NAME}"
```

### Installation Guide

See [Karpenter Installation Guide](https://karpenter.sh/docs/getting-started/getting-started-with-karpenter/)

Or use the Karpenter terraform module in `_module/karpenter.tf` (if available).
