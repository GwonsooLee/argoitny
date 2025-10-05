# AWS CloudFront 배포 가이드

이 가이드는 React + Vite 프론트엔드 애플리케이션을 AWS S3와 CloudFront를 사용하여 배포하는 전체 과정을 설명합니다.

## 목차
1. [사전 요구사항](#사전-요구사항)
2. [S3 버킷 생성 및 설정](#1-s3-버킷-생성-및-설정)
3. [빌드 및 업로드](#2-빌드-및-업로드)
4. [CloudFront 배포 설정](#3-cloudfront-배포-설정)
5. [도메인 연결](#4-도메인-연결-선택사항)
6. [배포 자동화](#5-배포-자동화)
7. [캐시 무효화](#6-캐시-무효화)
8. [문제 해결](#7-문제-해결)
9. [비용 정보](#8-비용-정보)

---

## 사전 요구사항

### 필수 도구
- **AWS CLI**: 최신 버전 설치
  ```bash
  # macOS
  brew install awscli

  # 또는 공식 설치 프로그램 사용
  curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
  sudo installer -pkg AWSCLIV2.pkg -target /
  ```

- **Node.js & npm**: v18 이상 권장
  ```bash
  node --version  # v18.x.x 이상
  npm --version   # v9.x.x 이상
  ```

### AWS 계정 및 권한
다음 권한이 필요한 IAM 사용자/역할:
- **S3**: `s3:CreateBucket`, `s3:PutObject`, `s3:PutObjectAcl`, `s3:DeleteObject`, `s3:ListBucket`
- **CloudFront**: `cloudfront:CreateDistribution`, `cloudfront:CreateInvalidation`, `cloudfront:GetDistribution`, `cloudfront:UpdateDistribution`
- **ACM**: `acm:RequestCertificate`, `acm:DescribeCertificate` (SSL 사용 시)
- **Route 53**: `route53:ChangeResourceRecordSets` (도메인 연결 시)

### AWS CLI 설정
```bash
# AWS 자격 증명 설정
aws configure

# 입력 사항:
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region name: us-east-1 (CloudFront SSL 인증서는 us-east-1 필수)
# Default output format: json
```

---

## 1. S3 버킷 생성 및 설정

### 1.1 S3 버킷 생성

```bash
# 버킷 이름 설정 (전역에서 고유해야 함)
BUCKET_NAME="algoitny-frontend-prod"
REGION="us-east-1"

# S3 버킷 생성
aws s3 mb s3://$BUCKET_NAME --region $REGION
```

### 1.2 정적 웹 호스팅 설정

```bash
# 정적 웹 호스팅 활성화
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html
```

**참고**: SPA(Single Page Application)의 경우 모든 라우팅을 `index.html`로 처리하기 위해 error-document도 `index.html`로 설정합니다.

### 1.3 버킷 정책 설정

CloudFront OAI(Origin Access Identity)를 사용하는 경우, 버킷은 private으로 유지하고 CloudFront만 접근 가능하도록 설정합니다.

**버킷 정책 파일 생성** (`s3-bucket-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontOAI",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity [YOUR_OAI_ID]"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::algoitny-frontend-prod/*"
    }
  ]
}
```

**참고**: `[YOUR_OAI_ID]`는 CloudFront OAI 생성 후 업데이트해야 합니다.

**Public Access로 설정하는 경우** (권장하지 않음):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::algoitny-frontend-prod/*"
    }
  ]
}
```

```bash
# 버킷 정책 적용
aws s3api put-bucket-policy \
  --bucket $BUCKET_NAME \
  --policy file://s3-bucket-policy.json
```

### 1.4 CORS 설정

백엔드 API와의 통신을 위해 CORS 설정이 필요할 수 있습니다.

**CORS 설정 파일 생성** (`s3-cors-config.json`):

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://api.testcase.run"],
      "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

```bash
# CORS 설정 적용
aws s3api put-bucket-cors \
  --bucket $BUCKET_NAME \
  --cors-configuration file://s3-cors-config.json
```

**참고**: 일반적으로 CORS는 백엔드 서버에서 설정하므로, S3 CORS는 선택사항입니다.

---

## 2. 빌드 및 업로드

### 2.1 프로덕션 빌드

```bash
# 프로젝트 디렉토리로 이동
cd /Users/gwonsoolee/algoitny/frontend

# 의존성 설치 (처음 한 번만)
npm install

# 프로덕션 빌드 (.env.production 자동 사용)
npm run build
```

빌드 산출물은 `dist/` 디렉토리에 생성됩니다.

### 2.2 S3에 수동 업로드

```bash
# dist 폴더 전체를 S3에 업로드
aws s3 sync dist/ s3://$BUCKET_NAME \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html"

# index.html은 캐싱 없이 업로드 (항상 최신 버전 제공)
aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html \
  --cache-control "public, max-age=0, must-revalidate"
```

**옵션 설명**:
- `--delete`: S3에 있지만 로컬에 없는 파일 삭제
- `--cache-control`: 브라우저 캐싱 정책 설정
  - 정적 자산(JS, CSS, 이미지): 1년 (31536000초)
  - `index.html`: 캐싱 안 함 (0초)

### 2.3 배포 스크립트 사용

제공된 배포 스크립트를 사용하면 더 간편합니다:

```bash
# 스크립트 실행 권한 부여
chmod +x deploy-scripts/deploy-to-s3.sh

# 배포 실행
./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod
```

---

## 3. CloudFront 배포 설정

### 3.1 Origin Access Identity (OAI) 생성

CloudFront에서만 S3 버킷에 접근할 수 있도록 OAI를 생성합니다.

```bash
# OAI 생성
aws cloudfront create-cloud-front-origin-access-identity \
  --cloud-front-origin-access-identity-config \
  CallerReference="algoitny-oai-$(date +%s)",Comment="OAI for algoitny frontend"

# 응답에서 OAI ID 확인 후 저장
# 예: E1XXXXXXXXXX
```

생성된 OAI ID를 S3 버킷 정책에 추가합니다 (1.3 단계 참조).

### 3.2 CloudFront Distribution 생성

**CloudFront 설정 파일 생성** (`cloudfront-config.json`):

```json
{
  "CallerReference": "algoitny-frontend-2025-01-01",
  "Comment": "Algoitny Frontend Distribution",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-algoitny-frontend-prod",
        "DomainName": "algoitny-frontend-prod.s3.us-east-1.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": "origin-access-identity/cloudfront/[YOUR_OAI_ID]"
        },
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-algoitny-frontend-prod",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "Compress": true,
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      },
      "Headers": {
        "Quantity": 0
      }
    }
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  },
  "PriceClass": "PriceClass_100"
}
```

**참고**:
- `[YOUR_OAI_ID]`를 실제 OAI ID로 교체
- `CallerReference`는 고유값 (타임스탬프 사용 권장)
- `PriceClass_100`: 북미/유럽만 (가장 저렴), `PriceClass_All`: 전 세계

### 3.3 AWS Console을 통한 생성 (권장)

CLI보다 AWS Console이 더 직관적입니다:

1. **AWS CloudFront Console** 접속: https://console.aws.amazon.com/cloudfront
2. **Create Distribution** 클릭
3. **Origin Settings**:
   - **Origin Domain**: S3 버킷 선택 (`algoitny-frontend-prod.s3.us-east-1.amazonaws.com`)
   - **Origin Access**: `Legacy access identities` 선택
   - **Origin Access Identity**: 새로 생성 또는 기존 OAI 선택
   - **Bucket Policy**: `Yes, update the bucket policy` 선택 (자동으로 S3 정책 업데이트)

4. **Default Cache Behavior**:
   - **Viewer Protocol Policy**: `Redirect HTTP to HTTPS`
   - **Allowed HTTP Methods**: `GET, HEAD`
   - **Cache Policy**: `CachingOptimized` (추천)
   - **Response Headers Policy**: `SimpleCORS` (필요 시)
   - **Compress Objects Automatically**: `Yes`

5. **Settings**:
   - **Price Class**: `Use Only North America and Europe` (비용 절감) 또는 `Use All Edge Locations`
   - **Alternate Domain Names (CNAMEs)**: 사용할 도메인 입력 (예: `app.testcase.run`)
   - **Custom SSL Certificate**: ACM에서 발급받은 인증서 선택
   - **Default Root Object**: `index.html`

6. **Custom Error Responses** (SPA 라우팅 지원):
   - **Create Custom Error Response** 클릭
   - **HTTP Error Code**: `403`
   - **Customize Error Response**: `Yes`
   - **Response Page Path**: `/index.html`
   - **HTTP Response Code**: `200`
   - 동일하게 `404` 에러도 추가

7. **Create Distribution** 클릭

배포가 완료되면 (Status: Deployed) CloudFront URL을 받습니다:
- 예: `https://d1234567890.cloudfront.net`

### 3.4 보안 헤더 설정 (Lambda@Edge 또는 Response Headers Policy)

**Response Headers Policy 생성** (AWS Console):

1. CloudFront > Policies > Response Headers 이동
2. **Create Policy** 클릭
3. **Security Headers** 설정:
   - **Strict-Transport-Security**: `max-age=63072000; includeSubdomains; preload`
   - **X-Content-Type-Options**: `nosniff`
   - **X-Frame-Options**: `DENY`
   - **X-XSS-Protection**: `1; mode=block`
   - **Referrer-Policy**: `strict-origin-when-cross-origin`
4. CloudFront Distribution의 Behavior에 정책 연결

---

## 4. 도메인 연결 (선택사항)

### 4.1 SSL/TLS 인증서 요청 (AWS Certificate Manager)

**중요**: CloudFront용 인증서는 반드시 **us-east-1 리전**에서 발급받아야 합니다.

```bash
# us-east-1 리전에서 인증서 요청
aws acm request-certificate \
  --domain-name app.testcase.run \
  --subject-alternative-names "*.testcase.run" \
  --validation-method DNS \
  --region us-east-1
```

**AWS Console에서 요청**:
1. **AWS Certificate Manager** (us-east-1 리전) 접속
2. **Request a certificate** 클릭
3. **Domain names**: `app.testcase.run` 입력
4. **Validation method**: `DNS validation` 선택
5. **Request** 클릭
6. **CNAME 레코드**를 도메인 DNS에 추가 (Route 53 또는 외부 DNS 제공자)
7. 검증 완료 후 인증서 상태가 **Issued**로 변경

### 4.2 Route 53 설정

**도메인이 Route 53에 있는 경우**:

1. **Route 53 Console** 접속
2. **Hosted zones** > 해당 도메인 선택
3. **Create record** 클릭
4. **Record type**: `A - IPv4 address`
5. **Alias**: `Yes`
6. **Route traffic to**: `Alias to CloudFront distribution`
7. **CloudFront distribution**: 생성한 Distribution 선택
8. **Create records** 클릭

**외부 DNS 제공자 사용 시**:
- **CNAME 레코드** 추가:
  - **Name**: `app` (또는 원하는 서브도메인)
  - **Type**: `CNAME`
  - **Value**: CloudFront Distribution URL (예: `d1234567890.cloudfront.net`)

### 4.3 CloudFront에 도메인 연결

1. CloudFront Distribution 편집
2. **Alternate Domain Names (CNAMEs)**: `app.testcase.run` 추가
3. **SSL Certificate**: 발급받은 ACM 인증서 선택
4. **Save changes**

---

## 5. 배포 자동화

### 5.1 GitHub Actions 워크플로우

프로젝트에 `.github/workflows/deploy-cloudfront.yml` 파일이 포함되어 있습니다.

**주요 기능**:
- `main` 브랜치에 push 시 자동 배포
- 프로덕션 빌드 생성
- S3에 파일 업로드
- CloudFront 캐시 무효화

**사용 방법**:

1. **GitHub Secrets 설정**:
   - Repository > Settings > Secrets and variables > Actions
   - 다음 secrets 추가:
     - `AWS_ACCESS_KEY_ID`: IAM 사용자 액세스 키
     - `AWS_SECRET_ACCESS_KEY`: IAM 사용자 시크릿 키
     - `AWS_REGION`: `us-east-1`
     - `S3_BUCKET_NAME`: `algoitny-frontend-prod`
     - `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront Distribution ID (예: `E1XXXXXXXXXX`)

2. **워크플로우 활성화**:
   - 파일이 `.github/workflows/` 디렉토리에 있으면 자동 활성화
   - `main` 브랜치에 push하면 배포 시작

3. **배포 상태 확인**:
   - GitHub Repository > Actions 탭에서 워크플로우 실행 상태 확인

### 5.2 수동 배포 스크립트

GitHub Actions를 사용하지 않는 경우, 제공된 스크립트 사용:

```bash
# S3 배포 + CloudFront 무효화
./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod E1XXXXXXXXXX
```

**스크립트 기능**:
- 프로덕션 빌드 생성
- S3에 파일 업로드 (최적화된 캐시 정책)
- CloudFront 캐시 자동 무효화

### 5.3 AWS CodeBuild/CodePipeline (선택사항)

더 복잡한 CI/CD 파이프라인을 원하는 경우 `buildspec.yml` 사용:

1. **AWS CodeBuild** 프로젝트 생성
2. **Source**: GitHub 연결
3. **Buildspec**: `buildspec.yml` 사용
4. **Artifacts**: S3 버킷 지정
5. **CodePipeline**으로 빌드 > 배포 자동화

---

## 6. 캐시 무효화

### 6.1 CloudFront 캐시 무효화 이유

새로운 버전을 배포한 후, CloudFront 엣지 로케이션에 캐시된 이전 파일들이 남아있을 수 있습니다. 캐시 무효화를 통해 즉시 새 버전을 제공할 수 있습니다.

### 6.2 수동 무효화

```bash
# Distribution ID 확인
aws cloudfront list-distributions --query "DistributionList.Items[*].[Id,Comment]" --output table

# 전체 캐시 무효화
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --paths "/*"

# 특정 경로만 무효화
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --paths "/index.html" "/static/*"
```

### 6.3 무효화 설정 파일

`cloudfront-invalidation.json`:

```json
{
  "Paths": {
    "Quantity": 1,
    "Items": ["/*"]
  },
  "CallerReference": "invalidation-2025-01-01-12-00-00"
}
```

```bash
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --invalidation-batch file://cloudfront-invalidation.json
```

### 6.4 자동 무효화 (배포 스크립트에 포함)

배포 스크립트와 GitHub Actions 워크플로우에 자동 무효화가 포함되어 있습니다.

**참고**: 매월 처음 1,000개 무효화 경로는 무료, 이후 경로당 $0.005입니다.

---

## 7. 문제 해결

### 7.1 일반적인 이슈

#### 문제: 404 에러 발생 (SPA 라우팅)

**원인**: CloudFront가 `/about` 같은 경로를 S3에서 찾으려 하지만 해당 파일이 없음

**해결**:
1. CloudFront > Error Pages > Custom Error Response 설정
2. 403, 404 에러를 `/index.html`로 리다이렉트 (Response Code: 200)

#### 문제: CORS 에러

**원인**: CloudFront가 CORS 헤더를 제대로 전달하지 않음

**해결**:
1. **백엔드에서 CORS 설정 확인** (Django의 경우 `django-cors-headers`)
2. CloudFront > Behaviors > Cache Policy에서 CORS 관련 헤더 forwarding 활성화
3. Response Headers Policy에 CORS 헤더 추가

#### 문제: 캐싱 문제 (새 버전이 반영되지 않음)

**원인**: CloudFront 엣지 캐시에 이전 버전이 남아있음

**해결**:
```bash
# 캐시 무효화
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --paths "/*"
```

또는 **배포 스크립트 사용** (자동 무효화 포함)

#### 문제: SSL 인증서 오류

**원인**: 인증서가 `us-east-1` 리전에 없거나, 도메인 검증 미완료

**해결**:
1. ACM 인증서가 **us-east-1 리전**에 있는지 확인
2. 인증서 상태가 **Issued**인지 확인
3. CNAME 레코드가 DNS에 올바르게 설정되었는지 확인

#### 문제: S3 Access Denied

**원인**: 버킷 정책이 올바르게 설정되지 않음

**해결**:
1. S3 버킷 정책에서 OAI가 `s3:GetObject` 권한을 가지는지 확인
2. CloudFront Distribution의 Origin Access 설정 확인

### 7.2 디버깅 팁

```bash
# CloudFront 배포 상태 확인
aws cloudfront get-distribution --id E1XXXXXXXXXX

# S3 버킷 내용 확인
aws s3 ls s3://algoitny-frontend-prod/ --recursive

# 최근 무효화 요청 확인
aws cloudfront list-invalidations --distribution-id E1XXXXXXXXXX

# CloudFront 로그 활성화 (S3 버킷 필요)
# Distribution 설정에서 Logging 활성화
```

### 7.3 브라우저 개발자 도구 활용

- **Network 탭**: CloudFront 응답 헤더 확인 (`X-Cache: Hit from cloudfront`)
- **Console 탭**: JavaScript 에러 확인
- **Application 탭**: 캐시 스토리지 확인

---

## 8. 비용 정보

### 8.1 예상 비용 (월별)

#### S3 스토리지
- **스토리지**: 빌드 파일 약 5MB → **$0.01/month** 미만
- **요청**: CloudFront에서만 접근 → **무시할 수 있는 수준**

#### CloudFront
- **데이터 전송** (미국/유럽 기준):
  - 처음 10TB: $0.085/GB
  - 월 1,000명 사용자, 평균 5MB 다운로드: 5GB → **$0.43/month**
- **HTTP/HTTPS 요청**:
  - 10,000 요청당 $0.01
  - 월 100,000 요청: **$0.10/month**
- **무효화**:
  - 월 1,000 경로까지 무료
  - 이후 경로당 $0.005

#### ACM (SSL 인증서)
- **무료** (퍼블릭 인증서)

#### Route 53 (도메인 사용 시)
- **Hosted Zone**: $0.50/month
- **쿼리**: 100만 건당 $0.40 (처음 10억 건)

### 8.2 총 예상 비용

**소규모 트래픽** (월 1,000 사용자):
- S3: $0.01
- CloudFront: $0.53
- Route 53: $0.50
- **총계**: **약 $1/month**

**중규모 트래픽** (월 10,000 사용자):
- S3: $0.01
- CloudFront: $5.30
- Route 53: $0.50
- **총계**: **약 $6/month**

**참고**:
- AWS 프리티어는 CloudFront 데이터 전송 50GB/월, S3 스토리지 5GB/월 무료 제공
- 실제 비용은 트래픽 패턴에 따라 다를 수 있음

### 8.3 비용 절감 팁

1. **PriceClass 최적화**: `PriceClass_100` (북미/유럽만) 사용
2. **캐싱 정책**: TTL을 길게 설정하여 Origin 요청 최소화
3. **압축**: Gzip/Brotli 압축으로 전송 데이터 감소
4. **무효화 최소화**: 필요한 경로만 무효화 (전체 무효화 자제)

---

## 9. 체크리스트

배포 전 확인 사항:

- [ ] AWS CLI 설치 및 설정 완료
- [ ] S3 버킷 생성 및 정책 설정
- [ ] CloudFront Distribution 생성
- [ ] Custom Error Response 설정 (403, 404 → index.html)
- [ ] HTTPS 리다이렉트 활성화
- [ ] 도메인 연결 (선택사항)
- [ ] SSL 인증서 발급 (도메인 사용 시)
- [ ] GitHub Secrets 설정 (자동 배포 시)
- [ ] 배포 스크립트 테스트
- [ ] 캐시 무효화 설정
- [ ] 프로덕션 환경 변수 확인 (.env.production)
- [ ] 빌드 테스트 (`npm run build`)
- [ ] 배포 후 기능 테스트

---

## 10. 추가 리소스

### 공식 문서
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)

### 도움말
- **AWS Support**: https://console.aws.amazon.com/support
- **AWS 프리티어**: https://aws.amazon.com/free/
- **CloudFront 요금**: https://aws.amazon.com/cloudfront/pricing/

---

## 요약

이 가이드를 따라하면 다음을 완료할 수 있습니다:

1. S3 버킷에 정적 파일 호스팅
2. CloudFront로 전 세계에 빠르게 콘텐츠 제공
3. HTTPS 보안 연결
4. SPA 라우팅 지원
5. 자동 배포 파이프라인 구축

배포 후에는 CloudFront URL 또는 연결한 도메인으로 애플리케이션에 접근할 수 있습니다.

**문제가 발생하면**:
- CloudWatch Logs 확인
- CloudFront 배포 상태 확인
- S3 버킷 정책 재확인
- 문제 해결 섹션 참조

Happy Deploying!
