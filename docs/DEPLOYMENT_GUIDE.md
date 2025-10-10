# AlgoItny Production Deployment Guide

## 📋 Overview

This guide covers the complete deployment of AlgoItny backend to AWS EKS with cost-optimized VPC Endpoints, IAM roles, and Helm charts.

## 🏗️ Infrastructure Components

### 1. VPC Endpoints (Cost Optimization)
- **S3 Gateway Endpoint**: No data transfer charges for S3 access within VPC
- **DynamoDB Gateway Endpoint**: No data transfer charges for DynamoDB access
- **Secrets Manager Interface Endpoint**: Reduces data transfer costs for secrets access

### 2. AWS Resources
- **DynamoDB Table**: `algoitny_main`
- **S3 Bucket**: `algoitny-testcases-zteapne2`
- **EKS Cluster**: With Karpenter, ALB Controller, External Secrets

### 3. Kubernetes Components
- **Gunicorn + Uvicorn**: ASGI server for async/await support
- **Celery Workers**: Task processing
- **Karpenter**: Node autoscaling
- **AWS Load Balancer Controller**: ALB ingress
- **External Secrets Operator**: AWS Secrets Manager integration

## 🚀 Deployment Steps

### Step 1: Deploy VPC Endpoints

```bash
# Navigate to VPC terraform directory
cd terraform/vpc/zte_apnortheast2

# Review changes
terraform plan

# Apply VPC endpoints (S3, DynamoDB, Secrets Manager)
terraform apply
```

**Cost Savings**: VPC Endpoints eliminate data transfer charges for AWS service access.

### Step 2: Deploy DynamoDB Table

```bash
# Navigate to DynamoDB terraform directory
cd terraform/dynamodb/algoitny/prod_apnortheast2

# Review table configuration
terraform plan

# Create DynamoDB table: algoitny_main
terraform apply
```

**Table Details**:
- Billing Mode: PAY_PER_REQUEST
- GSI1: User email lookup & search history
- GSI2: Google OAuth & public timeline
- GSI3: Problem status queries
- TTL enabled for usage log cleanup

### Step 3: Verify S3 Bucket

```bash
# Check if bucket exists
aws s3 ls | grep algoitny-testcases-zteapne2

# Expected output: algoitny-testcases-zteapne2
```

### Step 4: Deploy EKS IAM Roles

```bash
# Navigate to EKS terraform directory
cd terraform/eks/_module

# Review new IAM role for backend service
# File: algoitny_backend.tf

# Apply IAM roles
cd ../zte_apnortheast2/zteapne2-tfja  # or your EKS cluster directory
terraform apply
```

**IAM Role Created**:
- Name: `eks-{CLUSTER_NAME}-algoitny-backend`
- Permissions: DynamoDB (algoitny_main) + S3 (algoitny-testcases-zteapne2)
- Service Account: `production:algoitny-backend-sa`

### Step 5: Configure Helm Values

Edit `nest/values-production.yaml`:

```yaml
# Update YOUR_ACCOUNT_ID and cluster name
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/eks-algoitny-eks-cluster-algoitny-backend"
```

### Step 6: Deploy Backend with Helm

```bash
# From project root
cd nest

# Install External Secrets Operator (if not already installed)
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# Install AWS Load Balancer Controller (if not already installed)
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName=algoitny-eks-cluster

# Install Karpenter (if not already installed)
helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --namespace karpenter \
  --create-namespace \
  --version v0.32.0

# Deploy AlgoItny Backend
helm upgrade --install algoitny-backend . \
  -f values-production.yaml \
  --namespace production \
  --create-namespace
```

### Step 7: Verify Deployment

```bash
# Check pods
kubectl get pods -n production

# Check services
kubectl get svc -n production

# Check ingress (ALB)
kubectl get ingress -n production

# Check service account annotations
kubectl describe sa algoitny-backend-sa -n production

# Check external secrets
kubectl get externalsecrets -n production
kubectl get secretstore -n production

# View logs
kubectl logs -n production -l app.kubernetes.io/name=algoitny-backend --tail=100
```

## 🔍 Verification Checklist

- [ ] VPC Endpoints created (S3, DynamoDB, Secrets Manager)
- [ ] DynamoDB table `algoitny_main` exists
- [ ] S3 bucket `algoitny-testcases-zteapne2` accessible
- [ ] IAM role `eks-*-algoitny-backend` created
- [ ] Service account has correct role annotation
- [ ] External Secrets syncing from AWS Secrets Manager
- [ ] Pods have DynamoDB and S3 access
- [ ] ALB ingress created with HTTPS
- [ ] Karpenter provisioner active
- [ ] Health checks passing at `/api/health/`

## 🧪 Test AWS Access

```bash
# Get a shell in a pod
kubectl exec -it -n production deployment/algoitny-backend-gunicorn -- /bin/bash

# Test DynamoDB access
aws dynamodb describe-table --table-name algoitny_main --region ap-northeast-2

# Test S3 access
aws s3 ls s3://algoitny-testcases-zteapne2/ --region ap-northeast-2

# Exit pod
exit
```

## 📊 Cost Optimization Features

### VPC Endpoints
- ✅ **S3 Gateway Endpoint**: $0 data transfer (saves ~$0.09/GB)
- ✅ **DynamoDB Gateway Endpoint**: $0 data transfer (saves ~$0.09/GB)
- ✅ **Secrets Manager Interface**: ~$0.01/hour/AZ (~$7/month for 2 AZs)

### Karpenter
- ✅ Spot instances support (up to 90% cost savings)
- ✅ Automatic node consolidation
- ✅ Just-in-time provisioning

### DynamoDB
- ✅ On-demand pricing (pay per request)
- ✅ TTL for automatic cleanup
- ✅ Optimized GSI projections

### Expected Monthly Savings
- VPC Endpoints: **$50-100** (vs. NAT Gateway charges)
- Karpenter Spot: **$200-300** (vs. on-demand instances)
- **Total Savings**: **$250-400/month**

## 🔧 Environment Variables

The following environment variables are automatically configured:

```bash
# From ConfigMap
DEBUG=False
ALLOWED_HOSTS=api.testcase.run
AWS_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=algoitny_main
AWS_STORAGE_BUCKET_NAME=algoitny-testcases-zteapne2

# From AWS Secrets Manager (via External Secrets)
DATABASE_URL=<from-secrets>
REDIS_URL=<from-secrets>
CELERY_BROKER_URL=<from-secrets>
DJANGO_SECRET_KEY=<from-secrets>
GOOGLE_OAUTH_CLIENT_ID=<from-secrets>
GOOGLE_OAUTH_CLIENT_SECRET=<from-secrets>
GEMINI_API_KEY=<from-secrets>
```

## 📝 AWS Secrets Manager Structure

Create a secret at `algoitny/backend/prod` with:

```json
{
  "DATABASE_URL": "mysql://user:pass@host:3306/dbname",
  "REDIS_URL": "redis://redis-host:6379/0",
  "CELERY_BROKER_URL": "redis://redis-host:6379/0",
  "DJANGO_SECRET_KEY": "your-secret-key",
  "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
  "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret",
  "GOOGLE_OAUTH_REDIRECT_URI": "https://api.testcase.run/api/auth/google/callback/",
  "GEMINI_API_KEY": "your-gemini-api-key",
  "OPENAI_API_KEY": "your-openai-api-key",
  "JUDGE0_API_KEY": "your-judge0-api-key"
}
```

## 🚨 Troubleshooting

### Issue: Pods can't access DynamoDB

```bash
# Check IAM role annotation
kubectl describe sa algoitny-backend-sa -n production

# Check pod logs
kubectl logs -n production -l app.kubernetes.io/component=gunicorn --tail=100

# Verify IRSA setup
kubectl get sa algoitny-backend-sa -n production -o yaml
```

### Issue: External Secrets not syncing

```bash
# Check SecretStore
kubectl describe secretstore -n production

# Check ExternalSecret
kubectl describe externalsecret -n production

# Check logs
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

### Issue: ALB not created

```bash
# Check Ingress
kubectl describe ingress -n production

# Check ALB Controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

## 📚 Additional Resources

- [External Secrets Operator Docs](https://external-secrets.io/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Karpenter Documentation](https://karpenter.sh/)
- [VPC Endpoints Pricing](https://aws.amazon.com/privatelink/pricing/)

## ✅ Post-Deployment

After successful deployment:

1. Update DNS records to point to ALB endpoint
2. Configure CloudWatch alarms (already created by Terraform)
3. Set up monitoring dashboards
4. Test authentication flow
5. Run load tests
6. Configure backup policies

## 🔐 Security Best Practices

- ✅ Service Accounts use IRSA (no static credentials)
- ✅ Secrets stored in AWS Secrets Manager
- ✅ Private subnets for all pods
- ✅ Security groups restrict VPC endpoint access
- ✅ Pod security contexts enforced
- ✅ Network policies can be enabled

---

**Need Help?** Check the troubleshooting section or review Terraform/Helm logs for errors.
