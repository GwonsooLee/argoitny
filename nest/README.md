# AlgoItny Backend - EKS Deployment Guide

This Helm chart deploys the AlgoItny backend services to AWS EKS with the following components:

- **Gunicorn Deployment**: Django REST API server with HPA
- **Celery Worker Deployment**: Background task processing with KEDA autoscaling
- **Celery Beat Deployment**: Periodic task scheduler
- **External Secrets**: AWS Secrets Manager integration
- **ALB Ingress**: AWS Load Balancer Controller
- **Karpenter**: Node autoscaling
- **KEDA**: Kubernetes Event-Driven Autoscaling for Celery workers

## Prerequisites

### 1. EKS Cluster Setup

```bash
# Create EKS cluster with eksctl
eksctl create cluster \
  --name algoitny-eks-cluster \
  --version 1.28 \
  --region ap-northeast-2 \
  --nodegroup-name algoitny-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed \
  --tags Environment=production,Service=algoitny
```

### 2. Install Required Components

#### AWS Load Balancer Controller

```bash
# Add IAM policy for AWS Load Balancer Controller
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# Create service account with IRSA
eksctl create iamserviceaccount \
  --cluster=algoitny-eks-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=algoitny-eks-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

#### External Secrets Operator

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace \
  --set installCRDs=true
```

#### KEDA

```bash
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace
```

#### Karpenter

```bash
# Set environment variables
export CLUSTER_NAME=algoitny-eks-cluster
export AWS_REGION=ap-northeast-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create Karpenter IAM resources
curl -fsSL https://raw.githubusercontent.com/aws/karpenter/v0.32.0/website/content/en/preview/getting-started/getting-started-with-karpenter/cloudformation.yaml > karpenter-cfn.yaml

aws cloudformation deploy \
  --stack-name Karpenter-${CLUSTER_NAME} \
  --template-file karpenter-cfn.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ClusterName=${CLUSTER_NAME}

# Install Karpenter
helm repo add karpenter https://charts.karpenter.sh
helm repo update

helm upgrade --install karpenter karpenter/karpenter \
  --namespace karpenter \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME} \
  --set settings.aws.clusterName=${CLUSTER_NAME} \
  --set settings.aws.defaultInstanceProfile=KarpenterNodeInstanceProfile-${CLUSTER_NAME} \
  --set settings.aws.interruptionQueueName=${CLUSTER_NAME} \
  --wait
```

### 3. Setup AWS Resources

#### Create IAM Role for Service Account (IRSA)

```bash
# Create IAM policy for backend services
cat > algoitny-backend-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:ACCOUNT_ID:secret:algoitny/backend/prod-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::algoitny-backend-bucket",
        "arn:aws:s3:::algoitny-backend-bucket/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name AlgoItnyBackendPolicy \
  --policy-document file://algoitny-backend-policy.json

# Create service account with IRSA
eksctl create iamserviceaccount \
  --name algoitny-backend-sa \
  --namespace default \
  --cluster algoitny-eks-cluster \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/AlgoItnyBackendPolicy \
  --approve \
  --override-existing-serviceaccounts
```

#### Create Secrets in AWS Secrets Manager

```bash
# Create secret with all required environment variables
aws secretsmanager create-secret \
  --name algoitny/backend/prod \
  --description "AlgoItny Backend Production Secrets" \
  --secret-string '{
    "DATABASE_URL": "mysql://user:password@rds-endpoint:3306/algoitny",
    "REDIS_URL": "redis://redis-endpoint:6379/0",
    "CELERY_BROKER_URL": "redis://redis-endpoint:6379/0",
    "DJANGO_SECRET_KEY": "your-secret-key-here",
    "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
    "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret",
    "GOOGLE_OAUTH_REDIRECT_URI": "https://api.testcase.run/api/auth/google/callback/",
    "GEMINI_API_KEY": "your-gemini-api-key",
    "JUDGE0_API_KEY": "your-judge0-api-key",
    "AWS_ACCESS_KEY_ID": "your-aws-access-key",
    "AWS_SECRET_ACCESS_KEY": "your-aws-secret-key",
    "AWS_STORAGE_BUCKET_NAME": "algoitny-backend-bucket",
    "AWS_S3_REGION_NAME": "ap-northeast-2",
    "REDIS_PASSWORD": "your-redis-password"
  }' \
  --region ap-northeast-2
```

#### Create ACM Certificate

```bash
# Request certificate for api.testcase.run
aws acm request-certificate \
  --domain-name api.testcase.run \
  --validation-method DNS \
  --region ap-northeast-2

# Follow DNS validation steps in ACM console
```

### 4. Build and Push Docker Image

```bash
# Build Docker image
cd /Users/gwonsoolee/algoitny/backend
docker build -t algoitny-backend:latest .

# Tag and push to ECR
export ECR_REGISTRY=ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com
export REPOSITORY_NAME=algoitny-backend

# Create ECR repository
aws ecr create-repository --repository-name ${REPOSITORY_NAME} --region ap-northeast-2

# Login to ECR
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Tag and push
docker tag algoitny-backend:latest ${ECR_REGISTRY}/${REPOSITORY_NAME}:latest
docker push ${ECR_REGISTRY}/${REPOSITORY_NAME}:latest
```

## Installation

### 1. Update values.yaml

Edit `values.yaml` and update the following values:

```yaml
# Update ECR repository
image:
  repository: ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend
  tag: "latest"

# Update service account ARN
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT_ID:role/eksctl-algoitny-eks-cluster-addon-iamserviceac-Role1-XXX"

# Update Ingress certificate ARN
ingress:
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:ACCOUNT_ID:certificate/CERT_ID"

# Update KEDA Redis endpoint
celeryWorker:
  keda:
    triggers:
      - type: redis
        metadata:
          address: your-redis-endpoint:6379
```

### 2. Install Helm Chart

```bash
# Install or upgrade
helm upgrade --install algoitny-backend . \
  --namespace default \
  --create-namespace \
  --values values.yaml

# Check deployment status
kubectl get pods -n default
kubectl get ingress -n default
kubectl get hpa -n default
kubectl get scaledobject -n default
kubectl get provisioner
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -l app.kubernetes.io/name=algoitny-backend

# Check services
kubectl get svc -l app.kubernetes.io/name=algoitny-backend

# Check ingress and get ALB endpoint
kubectl get ingress algoitny-backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Check External Secrets
kubectl get externalsecret
kubectl get secretstore

# Check logs
kubectl logs -l app.kubernetes.io/component=gunicorn --tail=100
kubectl logs -l app.kubernetes.io/component=celery-worker --tail=100
kubectl logs -l app.kubernetes.io/component=celery-beat --tail=100

# Check HPA
kubectl get hpa

# Check KEDA ScaledObject
kubectl get scaledobject

# Check Karpenter Provisioner
kubectl get provisioner
```

### 4. Configure DNS

```bash
# Get ALB DNS name
ALB_DNS=$(kubectl get ingress algoitny-backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Create CNAME record: api.testcase.run -> ${ALB_DNS}"
```

## Scaling

### Gunicorn HPA
- Min: 2 replicas
- Max: 10 replicas
- Target CPU: 70%
- Target Memory: 80%

### Celery Worker KEDA
- Min: 2 replicas
- Max: 20 replicas
- Trigger: Redis queue length > 5 messages
- Polling interval: 30s
- Cooldown: 300s

### Karpenter Node Autoscaling
- Spot + On-Demand instances
- Instance types: c, m, r series (generation > 5)
- Max CPU: 100 cores
- Max Memory: 200Gi
- TTL after empty: 30s
- TTL until expired: 7 days

## Monitoring

```bash
# Watch pod autoscaling
watch kubectl get hpa
watch kubectl get scaledobject

# Watch node scaling
watch kubectl get nodes

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter

# Check KEDA logs
kubectl logs -n keda -l app.kubernetes.io/name=keda-operator
```

## Maintenance

### Update Application

```bash
# Build and push new image
docker build -t algoitny-backend:v1.1.0 .
docker tag algoitny-backend:v1.1.0 ${ECR_REGISTRY}/${REPOSITORY_NAME}:v1.1.0
docker push ${ECR_REGISTRY}/${REPOSITORY_NAME}:v1.1.0

# Update Helm chart
helm upgrade algoitny-backend . \
  --set image.tag=v1.1.0 \
  --namespace default
```

### Rollback

```bash
# Check history
helm history algoitny-backend

# Rollback to previous version
helm rollback algoitny-backend 1
```

### Update Secrets

```bash
# Update secrets in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id algoitny/backend/prod \
  --secret-string '{"KEY": "new-value"}' \
  --region ap-northeast-2

# Restart pods to pick up new secrets (after 1 hour refresh or manual restart)
kubectl rollout restart deployment/algoitny-backend-gunicorn
kubectl rollout restart deployment/algoitny-backend-celery-worker
kubectl rollout restart deployment/algoitny-backend-celery-beat
```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod POD_NAME

# Check logs
kubectl logs POD_NAME

# Check secrets
kubectl get secret algoitny-backend-secrets -o yaml
```

### Ingress not working

```bash
# Check ingress
kubectl describe ingress algoitny-backend

# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

### KEDA not scaling

```bash
# Check ScaledObject
kubectl describe scaledobject algoitny-backend-celery-worker

# Check KEDA operator logs
kubectl logs -n keda -l app.kubernetes.io/name=keda-operator

# Test Redis connection
kubectl run -it --rm redis-test --image=redis:alpine --restart=Never -- redis-cli -h REDIS_HOST ping
```

### Karpenter not provisioning nodes

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter

# Check provisioner
kubectl describe provisioner algoitny-backend

# Check pending pods
kubectl get pods --field-selector=status.phase=Pending
```

## Cost Optimization

1. **Spot Instances**: Karpenter uses spot instances (up to 70% savings)
2. **Autoscaling**: HPA and KEDA automatically scale down during low traffic
3. **Consolidation**: Karpenter consolidates nodes to reduce waste
4. **Right-sizing**: Monitor and adjust resource requests/limits

## Security

- ✅ IRSA for least-privilege IAM access
- ✅ External Secrets for sensitive data
- ✅ Non-root containers
- ✅ Read-only root filesystem (where possible)
- ✅ Network policies (optional)
- ✅ Pod Security Standards
- ✅ WAF integration on ALB
- ✅ HTTPS with ACM certificates

## Support

For issues or questions, please contact the AlgoItny team or create an issue in the repository.
