# AlgoItny Backend - EKS Deployment Quick Start

빠르게 EKS에 AlgoItny Backend를 배포하는 가이드입니다.

## 사전 준비

### 1. 필수 도구 설치

```bash
# AWS CLI
brew install awscli

# kubectl
brew install kubectl

# eksctl
brew install eksctl

# Helm
brew install helm

# AWS 계정 설정
aws configure
```

### 2. EKS 클러스터 생성

```bash
# eksctl로 클러스터 생성 (약 15분 소요)
eksctl create cluster \
  --name algoitny-eks-cluster \
  --version 1.28 \
  --region ap-northeast-2 \
  --nodegroup-name algoitny-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed

# 클러스터 확인
kubectl get nodes
```

### 3. 필수 애드온 설치

#### AWS Load Balancer Controller

```bash
# IAM 정책 생성
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# Service Account 생성
eksctl create iamserviceaccount \
  --cluster=algoitny-eks-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Helm으로 설치
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
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace \
  --set installCRDs=true
```

#### KEDA

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace
```

#### Karpenter (선택사항)

```bash
# Karpenter 설치 스크립트
curl -fsSL https://raw.githubusercontent.com/aws/karpenter/v0.32.0/website/content/en/preview/getting-started/getting-started-with-karpenter/cloudformation.yaml > karpenter-cfn.yaml

export CLUSTER_NAME=algoitny-eks-cluster
export AWS_REGION=ap-northeast-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws cloudformation deploy \
  --stack-name Karpenter-${CLUSTER_NAME} \
  --template-file karpenter-cfn.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ClusterName=${CLUSTER_NAME}

helm repo add karpenter https://charts.karpenter.sh
helm install karpenter karpenter/karpenter \
  --namespace karpenter \
  --create-namespace \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME} \
  --set settings.aws.clusterName=${CLUSTER_NAME} \
  --set settings.aws.defaultInstanceProfile=KarpenterNodeInstanceProfile-${CLUSTER_NAME} \
  --wait
```

## AWS 리소스 설정

### 1. RDS MySQL 생성

```bash
# RDS MySQL 인스턴스 생성 (예시)
aws rds create-db-instance \
  --db-instance-identifier algoitny-db \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --master-username admin \
  --master-user-password 'YourPassword123!' \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name default \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --region ap-northeast-2
```

### 2. ElastiCache Redis 생성

```bash
# ElastiCache Redis 클러스터 생성
aws elasticache create-replication-group \
  --replication-group-id algoitny-redis \
  --replication-group-description "AlgoItny Redis Cluster" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --region ap-northeast-2
```

### 3. ACM 인증서 생성

```bash
# SSL 인증서 요청
aws acm request-certificate \
  --domain-name api.testcase.run \
  --validation-method DNS \
  --region ap-northeast-2

# DNS 검증 후 인증서 ARN 확인
aws acm list-certificates --region ap-northeast-2
```

### 4. Secrets Manager에 시크릿 저장

```bash
# 시크릿 생성
aws secretsmanager create-secret \
  --name algoitny/backend/prod \
  --description "AlgoItny Backend Production Secrets" \
  --region ap-northeast-2

# 시크릿 값 설정
aws secretsmanager put-secret-value \
  --secret-id algoitny/backend/prod \
  --secret-string '{
    "DATABASE_URL": "mysql://admin:password@algoitny-db.xxxxx.ap-northeast-2.rds.amazonaws.com:3306/algoitny",
    "REDIS_URL": "redis://algoitny-redis.xxxxx.ng.0001.apn2.cache.amazonaws.com:6379/0",
    "CELERY_BROKER_URL": "redis://algoitny-redis.xxxxx.ng.0001.apn2.cache.amazonaws.com:6379/0",
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
    "REDIS_PASSWORD": ""
  }' \
  --region ap-northeast-2
```

### 5. IAM Role 생성 (IRSA)

```bash
# Backend용 IAM 정책 생성
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
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:algoitny/backend/prod-*"
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

# Service Account 생성
eksctl create iamserviceaccount \
  --name algoitny-backend-sa \
  --namespace default \
  --cluster algoitny-eks-cluster \
  --attach-policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AlgoItnyBackendPolicy \
  --approve
```

## 애플리케이션 배포

### 1. ECR 레포지토리 생성 및 이미지 빌드

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=ap-northeast-2
export ECR_REPOSITORY=algoitny-backend

# ECR 레포지토리 생성
aws ecr create-repository \
  --repository-name ${ECR_REPOSITORY} \
  --region ${AWS_REGION}

# 이미지 빌드 및 푸시 (스크립트 사용)
cd /Users/gwonsoolee/algoitny/nest/scripts
./build-and-push.sh v1.0.0
```

### 2. values-production.yaml 수정

```bash
cd /Users/gwonsoolee/algoitny/nest

# values-production.yaml 파일 수정
# - image.repository: ECR 레포지토리 URL
# - serviceAccount.annotations: IAM Role ARN
# - ingress.annotations.certificate-arn: ACM 인증서 ARN
# - celeryWorker.keda.triggers: Redis 엔드포인트
```

주요 수정 항목:

```yaml
image:
  repository: YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend
  tag: "v1.0.0"

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::YOUR_ACCOUNT_ID:role/eksctl-algoitny-eks-cluster-addon-iamserviceac-Role1-XXX"

ingress:
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:YOUR_ACCOUNT_ID:certificate/YOUR_CERT_ID"

celeryWorker:
  keda:
    triggers:
      - type: redis
        metadata:
          address: your-redis-endpoint.xxxxx.ng.0001.apn2.cache.amazonaws.com:6379
```

### 3. Helm으로 배포

```bash
# 배포 스크립트 사용
cd /Users/gwonsoolee/algoitny/nest/scripts
./deploy.sh production v1.0.0

# 또는 직접 Helm 명령어 사용
helm upgrade --install algoitny-backend ../nest \
  --namespace default \
  --create-namespace \
  --values ../nest/values-production.yaml \
  --set image.tag=v1.0.0 \
  --wait
```

### 4. 배포 확인

```bash
# Pod 상태 확인
kubectl get pods -l app.kubernetes.io/name=algoitny-backend

# 서비스 확인
kubectl get svc algoitny-backend

# Ingress 확인 (ALB DNS 확인)
kubectl get ingress algoitny-backend
ALB_DNS=$(kubectl get ingress algoitny-backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ALB DNS: ${ALB_DNS}"

# HPA 확인
kubectl get hpa

# KEDA ScaledObject 확인
kubectl get scaledobject

# 로그 확인
kubectl logs -l app.kubernetes.io/component=gunicorn --tail=100
kubectl logs -l app.kubernetes.io/component=celery-worker --tail=100
kubectl logs -l app.kubernetes.io/component=celery-beat --tail=100
```

### 5. DNS 설정

```bash
# Route 53에서 CNAME 레코드 생성
# api.testcase.run -> ALB_DNS
```

## 테스트

```bash
# Health check
curl https://api.testcase.run/api/health/

# API 테스트
curl https://api.testcase.run/api/problems/
```

## 모니터링

```bash
# 실시간 Pod 모니터링
watch kubectl get pods -l app.kubernetes.io/name=algoitny-backend

# HPA 모니터링
watch kubectl get hpa

# KEDA 스케일링 모니터링
watch kubectl get scaledobject

# 노드 모니터링
watch kubectl get nodes

# 로그 스트리밍
kubectl logs -f -l app.kubernetes.io/component=gunicorn
kubectl logs -f -l app.kubernetes.io/component=celery-worker
```

## 업데이트

```bash
# 새 버전 빌드 및 배포
cd /Users/gwonsoolee/algoitny/nest/scripts
./build-and-push.sh v1.1.0
./deploy.sh production v1.1.0
```

## 롤백

```bash
# Helm 히스토리 확인
helm history algoitny-backend

# 이전 버전으로 롤백
helm rollback algoitny-backend 1
```

## 삭제

```bash
# Helm 릴리스 삭제
helm uninstall algoitny-backend

# EKS 클러스터 삭제
eksctl delete cluster --name algoitny-eks-cluster
```

## 트러블슈팅

### Pod이 시작하지 않을 때

```bash
kubectl describe pod POD_NAME
kubectl logs POD_NAME
```

### ALB가 생성되지 않을 때

```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl describe ingress algoitny-backend
```

### KEDA 스케일링이 작동하지 않을 때

```bash
kubectl logs -n keda -l app.kubernetes.io/name=keda-operator
kubectl describe scaledobject algoitny-backend-celery-worker
```

## 비용 최적화

1. **Spot 인스턴스 사용**: Karpenter가 자동으로 Spot 인스턴스 활용
2. **오토스케일링**: 트래픽에 따라 자동으로 스케일 업/다운
3. **노드 통합**: Karpenter가 노드를 자동으로 통합하여 비용 절감
4. **리소스 모니터링**: CloudWatch로 리소스 사용량 모니터링 및 최적화

## 보안 체크리스트

- [x] IRSA로 최소 권한 IAM 역할 사용
- [x] External Secrets로 민감 정보 관리
- [x] Non-root 컨테이너 실행
- [x] HTTPS 적용 (ACM 인증서)
- [x] Security Group 설정
- [x] Network Policy 적용 (선택사항)
- [x] WAF 적용 (선택사항)

## 참고 자료

- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [External Secrets Operator](https://external-secrets.io/)
- [KEDA](https://keda.sh/)
- [Karpenter](https://karpenter.sh/)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
