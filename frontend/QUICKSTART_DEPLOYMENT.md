# AWS CloudFront 배포 빠른 시작 가이드

이 가이드는 최소한의 단계로 빠르게 배포하는 방법을 설명합니다. 상세한 설명은 [AWS_CLOUDFRONT_DEPLOYMENT.md](./AWS_CLOUDFRONT_DEPLOYMENT.md)를 참조하세요.

## 전제 조건

- AWS 계정
- AWS CLI 설치 및 설정 완료
- Node.js 18+ 설치

## 5분 안에 배포하기

### 1. AWS CLI 설정 (1분)

```bash
# AWS 자격 증명 설정
aws configure
# AWS Access Key ID: [입력]
# AWS Secret Access Key: [입력]
# Default region: us-east-1
# Default output format: json

# 확인
aws sts get-caller-identity
```

### 2. S3 버킷 생성 (1분)

```bash
# 버킷 이름 설정 (전역 고유해야 함)
BUCKET_NAME="algoitny-frontend-prod"

# 버킷 생성
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# 정적 웹 호스팅 활성화
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html
```

### 3. 빌드 및 배포 (2분)

```bash
# 프로젝트 디렉토리로 이동
cd /Users/gwonsoolee/algoitny/frontend

# 빌드
npm install
npm run build

# S3 업로드
aws s3 sync dist/ s3://$BUCKET_NAME \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html"

aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html \
  --cache-control "public, max-age=0, must-revalidate"
```

### 4. CloudFront 배포 생성 (AWS Console 사용, 1분)

1. [CloudFront Console](https://console.aws.amazon.com/cloudfront) 접속
2. **Create Distribution** 클릭
3. **Origin Domain**: S3 버킷 선택
4. **Origin Access**: Legacy access identities > Create new OAI
5. **Bucket Policy**: Yes, update the bucket policy
6. **Viewer Protocol Policy**: Redirect HTTP to HTTPS
7. **Default Root Object**: `index.html`
8. **Custom Error Responses** 추가:
   - Error code: 403, Response page: `/index.html`, Response code: 200
   - Error code: 404, Response page: `/index.html`, Response code: 200
9. **Create Distribution** 클릭

### 5. 배포 완료 확인

```bash
# CloudFront URL 확인 (배포 완료까지 5-10분 소요)
# 예: https://d1234567890.cloudfront.net
```

---

## 배포 스크립트 사용 (더 간단한 방법)

### 한 번만 실행

```bash
# 스크립트 실행 권한 부여
chmod +x deploy-scripts/deploy-to-s3.sh
```

### 배포 실행

```bash
# S3만 배포
./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod

# S3 + CloudFront 캐시 무효화
./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod E1XXXXXXXXXX
```

**참고**: `E1XXXXXXXXXX`는 CloudFront Distribution ID로 교체하세요.

---

## GitHub Actions 자동 배포 설정 (추천)

### 1. GitHub Secrets 추가

Repository > Settings > Secrets and variables > Actions

다음 Secrets 추가:
- `AWS_ACCESS_KEY_ID`: AWS Access Key
- `AWS_SECRET_ACCESS_KEY`: AWS Secret Key
- `AWS_REGION`: `us-east-1`
- `S3_BUCKET_NAME`: `algoitny-frontend-prod`
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront Distribution ID

상세 가이드: [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md)

### 2. 자동 배포 활성화

워크플로우 파일이 이미 포함되어 있습니다:
- `.github/workflows/deploy-cloudfront.yml`

`main` 브랜치에 push하면 자동으로 배포됩니다!

```bash
git add .
git commit -m "Setup CloudFront deployment"
git push origin main
```

GitHub Actions 탭에서 배포 상태를 확인할 수 있습니다.

---

## 다음 단계

### 도메인 연결 (선택사항)

1. **ACM 인증서 요청** (us-east-1 리전)
   - AWS Certificate Manager 접속
   - Request certificate
   - 도메인: `app.testcase.run`
   - Validation: DNS
   - CNAME 레코드 추가

2. **CloudFront에 도메인 연결**
   - Distribution 편집
   - Alternate Domain Names: `app.testcase.run`
   - SSL Certificate: 발급받은 인증서 선택

3. **DNS 설정**
   - Route 53 또는 외부 DNS에서 CNAME 추가
   - `app` → CloudFront Distribution URL

### 보안 강화

1. **Response Headers Policy 설정**
   - CloudFront > Policies > Response Headers
   - Security headers 추가 (HSTS, X-Frame-Options 등)

2. **S3 버킷 Public Access 차단**
   - CloudFront OAI만 접근 가능하도록 설정
   - 버킷 정책에서 OAI만 허용

### 모니터링

1. **CloudWatch Alarms 설정**
   - 에러율 모니터링
   - 트래픽 모니터링

2. **CloudFront 로깅 활성화**
   - 별도 S3 버킷에 로그 저장

---

## 문제 해결

### 404 에러 발생
- CloudFront Custom Error Responses 설정 확인
- 403, 404 → `/index.html` (Response Code: 200)

### CORS 에러
- 백엔드에서 CORS 설정 확인 (Django `django-cors-headers`)
- CloudFront Response Headers Policy에 CORS 추가

### 캐싱 문제
```bash
# CloudFront 캐시 무효화
aws cloudfront create-invalidation \
  --distribution-id E1XXXXXXXXXX \
  --paths "/*"
```

### Access Denied
- S3 버킷 정책 확인
- CloudFront OAI 설정 확인

---

## 유용한 명령어

```bash
# CloudFront Distribution 목록
aws cloudfront list-distributions \
  --query "DistributionList.Items[*].[Id,Comment,DomainName]" \
  --output table

# S3 버킷 내용 확인
aws s3 ls s3://algoitny-frontend-prod/ --recursive

# 최근 무효화 요청 확인
aws cloudfront list-invalidations \
  --distribution-id E1XXXXXXXXXX

# CloudFront Distribution 상태 확인
aws cloudfront get-distribution \
  --id E1XXXXXXXXXX \
  --query "Distribution.Status" \
  --output text
```

---

## 비용 예상

**소규모 트래픽** (월 1,000 사용자):
- **약 $1/month**

**중규모 트래픽** (월 10,000 사용자):
- **약 $6/month**

AWS 프리티어:
- CloudFront: 50GB 데이터 전송/월
- S3: 5GB 스토리지/월

---

## 참고 문서

- [상세 배포 가이드](./AWS_CLOUDFRONT_DEPLOYMENT.md)
- [배포 체크리스트](./DEPLOYMENT_CHECKLIST.md)
- [GitHub Secrets 설정](./GITHUB_SECRETS_SETUP.md)

---

**배포 완료! 이제 전 세계 사용자에게 빠르게 앱을 제공할 수 있습니다.**
