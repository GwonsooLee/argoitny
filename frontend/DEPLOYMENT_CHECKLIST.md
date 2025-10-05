# AWS CloudFront 배포 체크리스트

이 체크리스트를 사용하여 배포 전후 필요한 모든 단계를 확인하세요.

## 배포 전 준비 사항

### 1. AWS 계정 및 자격 증명
- [ ] AWS 계정 생성 완료
- [ ] IAM 사용자 생성 (또는 적절한 권한이 있는 역할)
- [ ] AWS CLI 설치 완료
- [ ] AWS CLI 자격 증명 설정 (`aws configure`)
- [ ] AWS 자격 증명 테스트 (`aws sts get-caller-identity`)

### 2. 필수 권한 확인
- [ ] S3 권한: `s3:CreateBucket`, `s3:PutObject`, `s3:PutObjectAcl`, `s3:DeleteObject`, `s3:ListBucket`
- [ ] CloudFront 권한: `cloudfront:CreateDistribution`, `cloudfront:CreateInvalidation`, `cloudfront:GetDistribution`
- [ ] ACM 권한 (SSL 사용 시): `acm:RequestCertificate`, `acm:DescribeCertificate`
- [ ] Route 53 권한 (도메인 연결 시): `route53:ChangeResourceRecordSets`

### 3. 프로젝트 설정
- [ ] Node.js 설치 (v18 이상)
- [ ] 프로젝트 의존성 설치 (`npm install`)
- [ ] `.env.production` 파일 확인 및 설정
  - [ ] `VITE_API_URL=https://api.testcase.run/api` 설정 확인
  - [ ] `VITE_ENV=production` 설정 확인
- [ ] 로컬 빌드 테스트 (`npm run build`)
- [ ] 빌드 결과 확인 (`dist/` 디렉토리 및 `index.html` 존재)

---

## S3 설정

### 1. S3 버킷 생성
- [ ] 버킷 이름 결정 (전역 고유, 예: `algoitny-frontend-prod`)
- [ ] 리전 선택 (`us-east-1` 권장)
- [ ] S3 버킷 생성
  ```bash
  aws s3 mb s3://algoitny-frontend-prod --region us-east-1
  ```

### 2. S3 버킷 설정
- [ ] 정적 웹 호스팅 활성화
  ```bash
  aws s3 website s3://algoitny-frontend-prod \
    --index-document index.html \
    --error-document index.html
  ```
- [ ] 버킷 정책 설정 (OAI 사용 또는 Public Read)
  - [ ] `s3-bucket-policy.json` 파일 수정 (OAI ID 또는 버킷 이름)
  - [ ] 버킷 정책 적용
    ```bash
    aws s3api put-bucket-policy \
      --bucket algoitny-frontend-prod \
      --policy file://s3-bucket-policy.json
    ```
- [ ] CORS 설정 (선택사항)
  ```bash
  aws s3api put-bucket-cors \
    --bucket algoitny-frontend-prod \
    --cors-configuration file://s3-cors-config.json
  ```

---

## CloudFront 설정

### 1. Origin Access Identity (OAI) 생성
- [ ] CloudFront OAI 생성
  ```bash
  aws cloudfront create-cloud-front-origin-access-identity \
    --cloud-front-origin-access-identity-config \
    CallerReference="algoitny-oai-$(date +%s)",Comment="OAI for algoitny frontend"
  ```
- [ ] OAI ID 저장 (예: `E1XXXXXXXXXX`)
- [ ] S3 버킷 정책에 OAI 추가

### 2. CloudFront Distribution 생성
- [ ] AWS CloudFront Console 접속
- [ ] Create Distribution 클릭
- [ ] Origin Settings 설정:
  - [ ] Origin Domain: S3 버킷 선택
  - [ ] Origin Access: Legacy access identities
  - [ ] OAI 선택 및 버킷 정책 자동 업데이트
- [ ] Default Cache Behavior 설정:
  - [ ] Viewer Protocol Policy: Redirect HTTP to HTTPS
  - [ ] Allowed HTTP Methods: GET, HEAD
  - [ ] Compress Objects: Yes
- [ ] Settings:
  - [ ] Price Class 선택 (북미/유럽 또는 전 세계)
  - [ ] Default Root Object: `index.html`
- [ ] Custom Error Responses:
  - [ ] 403 에러 → `/index.html` (Response Code: 200)
  - [ ] 404 에러 → `/index.html` (Response Code: 200)
- [ ] Create Distribution 클릭
- [ ] Distribution ID 저장 (예: `E2YYYYYYYYYY`)

### 3. 보안 헤더 설정
- [ ] Response Headers Policy 생성 (또는 기존 정책 사용)
- [ ] Security Headers 설정:
  - [ ] Strict-Transport-Security
  - [ ] X-Content-Type-Options
  - [ ] X-Frame-Options
  - [ ] X-XSS-Protection
  - [ ] Referrer-Policy
- [ ] CloudFront Behavior에 정책 연결

---

## SSL/TLS 인증서 (도메인 사용 시)

### 1. ACM 인증서 요청
- [ ] AWS Certificate Manager (us-east-1 리전) 접속
- [ ] Request a certificate 클릭
- [ ] 도메인 이름 입력 (예: `app.testcase.run`)
- [ ] Validation method: DNS validation
- [ ] Request 클릭
- [ ] CNAME 레코드를 DNS에 추가
- [ ] 인증서 상태가 "Issued"로 변경 대기

### 2. CloudFront에 SSL 인증서 연결
- [ ] CloudFront Distribution 편집
- [ ] Alternate Domain Names (CNAMEs) 추가 (예: `app.testcase.run`)
- [ ] SSL Certificate 선택 (발급받은 ACM 인증서)
- [ ] Save changes

---

## 도메인 연결 (Route 53 또는 외부 DNS)

### Route 53 사용 시
- [ ] Route 53 Console 접속
- [ ] Hosted zones 선택
- [ ] Create record 클릭
- [ ] Record type: A (IPv4)
- [ ] Alias: Yes
- [ ] Route traffic to: CloudFront distribution
- [ ] Distribution 선택
- [ ] Create records

### 외부 DNS 제공자 사용 시
- [ ] CNAME 레코드 추가
  - Name: `app` (서브도메인)
  - Type: `CNAME`
  - Value: CloudFront Distribution URL (예: `d1234567890.cloudfront.net`)

---

## GitHub Actions 자동 배포 설정

### 1. GitHub Secrets 설정
- [ ] Repository > Settings > Secrets and variables > Actions 접속
- [ ] 다음 Secrets 추가:
  - [ ] `AWS_ACCESS_KEY_ID`: IAM 사용자 액세스 키
  - [ ] `AWS_SECRET_ACCESS_KEY`: IAM 사용자 시크릿 키
  - [ ] `AWS_REGION`: `us-east-1`
  - [ ] `S3_BUCKET_NAME`: `algoitny-frontend-prod`
  - [ ] `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront Distribution ID

### 2. 워크플로우 파일 확인
- [ ] `.github/workflows/deploy-cloudfront.yml` 파일 존재 확인
- [ ] 워크플로우 설정 검토 (트리거 브랜치, 환경 변수 등)

### 3. 자동 배포 테스트
- [ ] `main` 브랜치에 코드 push
- [ ] GitHub Actions 탭에서 워크플로우 실행 상태 확인
- [ ] 배포 완료 후 사이트 접속 확인

---

## 수동 배포 (스크립트 사용)

### 1. 배포 스크립트 실행 권한
- [ ] 스크립트 실행 권한 부여
  ```bash
  chmod +x deploy-scripts/deploy-to-s3.sh
  ```

### 2. 배포 실행
- [ ] 배포 스크립트 실행
  ```bash
  ./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod E2YYYYYYYYYY
  ```
- [ ] 빌드 및 업로드 완료 확인
- [ ] CloudFront 캐시 무효화 완료 확인

---

## 배포 후 확인 사항

### 1. 기본 접근 확인
- [ ] CloudFront URL로 사이트 접속 (예: `https://d1234567890.cloudfront.net`)
- [ ] 커스텀 도메인으로 접속 (설정한 경우, 예: `https://app.testcase.run`)
- [ ] HTTPS 리다이렉트 확인 (HTTP로 접속 시 HTTPS로 리다이렉트)

### 2. 기능 테스트
- [ ] 홈페이지 로딩 확인
- [ ] SPA 라우팅 확인 (다른 페이지로 이동 후 새로고침)
- [ ] API 통신 확인 (백엔드 API 호출 테스트)
- [ ] Google OAuth 로그인 (설정된 경우)
- [ ] 모든 주요 기능 테스트

### 3. 성능 확인
- [ ] 페이지 로딩 속도 확인
- [ ] 브라우저 개발자 도구 > Network 탭 확인
  - [ ] 정적 자산 캐싱 확인 (`X-Cache: Hit from cloudfront`)
  - [ ] Gzip/Brotli 압축 확인
- [ ] Google PageSpeed Insights 테스트
- [ ] Lighthouse 점수 확인

### 4. 보안 확인
- [ ] SSL/TLS 인증서 유효성 확인
- [ ] Security Headers 확인 (개발자 도구 > Network > Response Headers)
  - [ ] `Strict-Transport-Security`
  - [ ] `X-Content-Type-Options`
  - [ ] `X-Frame-Options`
  - [ ] `X-XSS-Protection`
- [ ] Mixed Content 경고 없음 확인

### 5. 브라우저 호환성
- [ ] Chrome 테스트
- [ ] Firefox 테스트
- [ ] Safari 테스트
- [ ] Edge 테스트
- [ ] 모바일 브라우저 테스트 (iOS Safari, Chrome Android)

---

## 모니터링 및 유지보수

### 1. CloudWatch 설정
- [ ] CloudFront 로깅 활성화 (선택사항)
- [ ] S3 버킷 로그 저장 설정
- [ ] CloudWatch Alarms 설정 (트래픽, 에러율 등)

### 2. 정기 점검
- [ ] 주간 트래픽 확인
- [ ] 월간 비용 확인 (AWS Cost Explorer)
- [ ] SSL 인증서 만료일 확인 (ACM은 자동 갱신)
- [ ] CloudFront 캐시 히트율 확인

### 3. 업데이트 프로세스
- [ ] 코드 변경 후 빌드 테스트
- [ ] `main` 브랜치에 merge (GitHub Actions 자동 배포)
- [ ] 또는 수동 배포 스크립트 실행
- [ ] 배포 후 기능 테스트
- [ ] 문제 발생 시 롤백 계획

---

## 문제 해결

### 일반적인 이슈 확인
- [ ] CloudFront 배포 상태 확인 (`aws cloudfront get-distribution --id YOUR_DIST_ID`)
- [ ] S3 버킷 내용 확인 (`aws s3 ls s3://algoitny-frontend-prod/ --recursive`)
- [ ] CloudFront 캐시 무효화 상태 확인
- [ ] 브라우저 캐시 클리어 후 재시도
- [ ] AWS CloudWatch Logs 확인

### 에러별 해결 방법
- [ ] 404 에러: Custom Error Response 설정 확인
- [ ] CORS 에러: 백엔드 CORS 설정 및 CloudFront Response Headers Policy 확인
- [ ] SSL 에러: ACM 인증서 리전 및 도메인 검증 확인
- [ ] Access Denied: S3 버킷 정책 및 CloudFront OAI 설정 확인

---

## 참고 문서
- [AWS CloudFront Deployment Guide](./AWS_CLOUDFRONT_DEPLOYMENT.md)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)

---

## 완료 서명

배포 완료 날짜: _______________

담당자: _______________

검수자: _______________

비고: _______________
