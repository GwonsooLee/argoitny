# AWS 권한 요구사항

AWS CloudFront 배포에 필요한 IAM 권한 목록입니다.

## 1. 최소 권한 정책 (Minimum Required Permissions)

배포를 위해 반드시 필요한 권한들입니다.

### IAM Policy JSON

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3BucketManagement",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:GetBucketPolicy",
        "s3:PutBucketPolicy",
        "s3:PutBucketWebsite",
        "s3:PutBucketCORS"
      ],
      "Resource": "arn:aws:s3:::algoitny-frontend-*"
    },
    {
      "Sid": "S3ObjectManagement",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::algoitny-frontend-*/*"
    },
    {
      "Sid": "CloudFrontDistributionManagement",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:GetDistributionConfig",
        "cloudfront:UpdateDistribution",
        "cloudfront:ListDistributions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFrontOAIManagement",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateCloudFrontOriginAccessIdentity",
        "cloudfront:GetCloudFrontOriginAccessIdentity",
        "cloudfront:ListCloudFrontOriginAccessIdentities"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFrontInvalidation",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ACMCertificateManagement",
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "Route53DomainManagement",
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:GetChange",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

## 2. 배포 자동화용 권한 (GitHub Actions)

GitHub Actions에서 사용할 최소 권한입니다.

### IAM Policy JSON (`github-actions-policy.json`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Deployment",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::algoitny-frontend-prod",
        "arn:aws:s3:::algoitny-frontend-prod/*"
      ]
    },
    {
      "Sid": "CloudFrontInvalidation",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations",
        "cloudfront:GetDistribution"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. 권한 설명

### S3 권한

| 권한 | 설명 | 필수 여부 |
|------|------|----------|
| `s3:CreateBucket` | S3 버킷 생성 | 초기 설정 시 |
| `s3:ListBucket` | 버킷 내용 목록 조회 | 필수 |
| `s3:PutObject` | 파일 업로드 | 필수 |
| `s3:PutObjectAcl` | 파일 접근 권한 설정 | 필수 |
| `s3:GetObject` | 파일 다운로드 | 선택 |
| `s3:DeleteObject` | 파일 삭제 | 필수 (sync --delete 사용 시) |
| `s3:PutBucketPolicy` | 버킷 정책 설정 | 초기 설정 시 |
| `s3:PutBucketWebsite` | 정적 웹 호스팅 설정 | 초기 설정 시 |
| `s3:PutBucketCORS` | CORS 설정 | 선택 |

### CloudFront 권한

| 권한 | 설명 | 필수 여부 |
|------|------|----------|
| `cloudfront:CreateDistribution` | Distribution 생성 | 초기 설정 시 |
| `cloudfront:GetDistribution` | Distribution 정보 조회 | 필수 |
| `cloudfront:UpdateDistribution` | Distribution 설정 변경 | 선택 |
| `cloudfront:ListDistributions` | Distribution 목록 조회 | 선택 |
| `cloudfront:CreateInvalidation` | 캐시 무효화 | 필수 |
| `cloudfront:GetInvalidation` | 무효화 상태 조회 | 선택 |
| `cloudfront:CreateCloudFrontOriginAccessIdentity` | OAI 생성 | 초기 설정 시 |

### ACM 권한 (SSL 인증서)

| 권한 | 설명 | 필수 여부 |
|------|------|----------|
| `acm:RequestCertificate` | 인증서 요청 | 도메인 사용 시 |
| `acm:DescribeCertificate` | 인증서 상태 확인 | 도메인 사용 시 |
| `acm:ListCertificates` | 인증서 목록 조회 | 선택 |

**중요**: ACM 인증서는 반드시 `us-east-1` 리전에서 발급받아야 합니다.

### Route 53 권한 (도메인 연결)

| 권한 | 설명 | 필수 여부 |
|------|------|----------|
| `route53:ChangeResourceRecordSets` | DNS 레코드 변경 | 도메인 사용 시 |
| `route53:GetChange` | 변경 상태 확인 | 선택 |
| `route53:ListHostedZones` | Hosted Zone 목록 | 선택 |

## 4. IAM 사용자 생성 및 정책 적용

### 4.1 IAM 사용자 생성

```bash
# IAM 사용자 생성
aws iam create-user --user-name algoitny-deployment

# Access Key 생성
aws iam create-access-key --user-name algoitny-deployment
```

**출력 예시**:
```json
{
  "AccessKey": {
    "UserName": "algoitny-deployment",
    "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
    "Status": "Active",
    "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  }
}
```

**중요**: `AccessKeyId`와 `SecretAccessKey`를 안전하게 저장하세요!

### 4.2 정책 생성 및 연결

```bash
# 계정 ID 확인
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 정책 생성 (초기 설정용)
aws iam create-policy \
  --policy-name AlgoitnyFullDeploymentPolicy \
  --policy-document file://aws-full-deployment-policy.json

# 정책 ARN
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/AlgoitnyFullDeploymentPolicy"

# 사용자에게 정책 연결
aws iam attach-user-policy \
  --user-name algoitny-deployment \
  --policy-arn $POLICY_ARN
```

### 4.3 GitHub Actions용 정책 (배포만)

```bash
# GitHub Actions용 정책 생성
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-policy.json

# GitHub Actions용 사용자 생성
aws iam create-user --user-name github-actions-deploy

# Access Key 생성
aws iam create-access-key --user-name github-actions-deploy

# 정책 연결
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/GitHubActionsDeployPolicy
```

## 5. 권한 검증

### 5.1 S3 권한 테스트

```bash
# 버킷 생성 테스트
aws s3 mb s3://test-bucket-$(date +%s)

# 파일 업로드 테스트
echo "test" > test.txt
aws s3 cp test.txt s3://algoitny-frontend-prod/test.txt

# 파일 삭제 테스트
aws s3 rm s3://algoitny-frontend-prod/test.txt
```

### 5.2 CloudFront 권한 테스트

```bash
# Distribution 목록 조회
aws cloudfront list-distributions

# Distribution 정보 조회
aws cloudfront get-distribution --id E1XXXXXXXXXX

# 캐시 무효화 테스트
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --paths "/test.txt"
```

### 5.3 ACM 권한 테스트

```bash
# 인증서 목록 조회 (us-east-1)
aws acm list-certificates --region us-east-1

# 인증서 요청 테스트 (실제로 요청하지 말고 dry-run)
aws acm request-certificate \
  --domain-name test.example.com \
  --validation-method DNS \
  --region us-east-1 \
  --dry-run
```

## 6. 보안 모범 사례

### 6.1 최소 권한 원칙
- 필요한 최소한의 권한만 부여
- 초기 설정 후에는 더 제한적인 정책 사용
- GitHub Actions용 계정은 S3 업로드와 CloudFront 무효화만 가능

### 6.2 Access Key 관리
- Access Key 정기 교체 (90일마다)
- 사용하지 않는 Key 즉시 비활성화
- AWS Secrets Manager 또는 SSM Parameter Store 사용 고려

### 6.3 MFA (다단계 인증)
```bash
# MFA 활성화 (권장)
aws iam enable-mfa-device \
  --user-name algoitny-deployment \
  --serial-number arn:aws:iam::ACCOUNT_ID:mfa/algoitny-deployment \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

### 6.4 CloudTrail 로깅
```bash
# API 호출 기록 확인
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=github-actions-deploy \
  --max-results 10
```

### 6.5 Resource Tagging
모든 리소스에 태그 추가:
- `Project`: `algoitny`
- `Environment`: `production`
- `ManagedBy`: `github-actions`

## 7. 권한 문제 해결

### Access Denied 에러

**원인**: 권한 부족

**해결**:
1. IAM Console에서 사용자 권한 확인
2. 정책이 올바르게 연결되었는지 확인
3. 리소스 ARN이 정확한지 확인
4. CloudTrail 로그에서 거부된 API 호출 확인

### 잘못된 자격 증명

**원인**: Access Key가 잘못되거나 비활성화됨

**해결**:
```bash
# 현재 자격 증명 확인
aws sts get-caller-identity

# Access Key 목록 확인
aws iam list-access-keys --user-name github-actions-deploy

# 새 Access Key 생성
aws iam create-access-key --user-name github-actions-deploy
```

## 8. 체크리스트

권한 설정 전 확인:

- [ ] AWS 계정 생성 완료
- [ ] IAM 사용자 생성 완료
- [ ] Access Key 생성 및 저장
- [ ] 필요한 정책 생성 (초기 설정용 또는 배포용)
- [ ] 사용자에게 정책 연결
- [ ] 권한 테스트 완료 (S3, CloudFront)
- [ ] GitHub Secrets 설정 (자동 배포 시)
- [ ] Access Key 보안 저장소에 백업

## 9. 참고 문서

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Policy Generator](https://awspolicygen.s3.amazonaws.com/policygen.html)
- [CloudFront Permissions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/access-control-overview.html)
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)

---

**문제가 발생하면 AWS Support에 문의하거나 CloudTrail 로그를 확인하세요.**
