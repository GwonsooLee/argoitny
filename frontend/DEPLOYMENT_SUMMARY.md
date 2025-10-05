# AWS CloudFront 배포 - 완료 요약

이 문서는 AWS CloudFront 배포 가이드 작성 작업의 완료 요약입니다.

## 생성된 파일 목록

### 1. 주요 가이드 문서

| 파일명 | 설명 | 용도 |
|--------|------|------|
| `AWS_CLOUDFRONT_DEPLOYMENT.md` | 상세 배포 가이드 | 전체 배포 프로세스 단계별 설명 |
| `QUICKSTART_DEPLOYMENT.md` | 빠른 시작 가이드 | 5분 안에 배포하는 방법 |
| `DEPLOYMENT_CHECKLIST.md` | 배포 체크리스트 | 배포 전후 확인 사항 |
| `GITHUB_SECRETS_SETUP.md` | GitHub Secrets 설정 가이드 | 자동 배포를 위한 Secrets 설정 |
| `AWS_PERMISSIONS_REQUIRED.md` | AWS 권한 요구사항 | 필요한 IAM 권한 목록 |
| `AWS_COST_ESTIMATION.md` | 비용 예상 | 사용량별 비용 분석 및 절감 방법 |
| `DEPLOYMENT_SUMMARY.md` | 배포 요약 (이 문서) | 전체 작업 요약 |

### 2. 설정 파일

| 파일명 | 설명 | 용도 |
|--------|------|------|
| `s3-bucket-policy.json` | S3 버킷 정책 | CloudFront OAI 접근 허용 |
| `s3-cors-config.json` | S3 CORS 설정 | CORS 규칙 (선택사항) |
| `cloudfront-invalidation.json` | CloudFront 무효화 설정 | 수동 캐시 무효화용 |
| `github-actions-policy.json` | IAM 정책 | GitHub Actions용 최소 권한 |
| `buildspec.yml` | CodeBuild 빌드 설정 | AWS CodeBuild 사용 시 |

### 3. 배포 자동화

| 파일명 | 설명 | 용도 |
|--------|------|------|
| `.github/workflows/deploy-cloudfront.yml` | GitHub Actions 워크플로우 | 자동 배포 파이프라인 |
| `deploy-scripts/deploy-to-s3.sh` | 배포 스크립트 | 수동 배포 스크립트 |

### 4. 기타

| 파일명 | 설명 | 용도 |
|--------|------|------|
| `README.md` | 프로젝트 README (업데이트) | 프로젝트 개요 및 배포 링크 |

---

## 배포 단계별 가이드 요약

### Phase 1: 사전 준비 (10분)

1. **AWS CLI 설치 및 설정**
   ```bash
   aws configure
   ```

2. **IAM 사용자 생성 및 권한 부여**
   - 정책: `github-actions-policy.json` 사용
   - 권한: S3, CloudFront

3. **환경 변수 확인**
   - `.env.production` 파일 확인
   - `VITE_API_URL=https://api.testcase.run/api`

### Phase 2: S3 설정 (5분)

1. **S3 버킷 생성**
   ```bash
   aws s3 mb s3://algoitny-frontend-prod --region us-east-1
   ```

2. **정적 웹 호스팅 활성화**
   ```bash
   aws s3 website s3://algoitny-frontend-prod \
     --index-document index.html \
     --error-document index.html
   ```

3. **버킷 정책 설정**
   - `s3-bucket-policy.json` 파일 사용
   - CloudFront OAI ID 업데이트 필요

### Phase 3: CloudFront 설정 (10분)

1. **OAI 생성**
   - AWS CloudFront Console에서 생성

2. **Distribution 생성**
   - Origin: S3 버킷
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Custom Error Responses: 403, 404 → `/index.html`

3. **보안 헤더 설정**
   - Response Headers Policy 생성
   - Security headers 추가

### Phase 4: 도메인 연결 (선택사항, 15분)

1. **ACM 인증서 요청 (us-east-1)**
   - 도메인: `app.testcase.run`
   - Validation: DNS

2. **CloudFront에 도메인 연결**
   - Alternate Domain Names 추가
   - SSL Certificate 선택

3. **Route 53 또는 외부 DNS 설정**
   - CNAME 또는 Alias 레코드 추가

### Phase 5: 자동 배포 설정 (5분)

1. **GitHub Secrets 추가**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `S3_BUCKET_NAME`
   - `CLOUDFRONT_DISTRIBUTION_ID`

2. **워크플로우 활성화**
   - `.github/workflows/deploy-cloudfront.yml` 파일이 자동으로 활성화됨
   - `main` 브랜치에 push 시 자동 배포

### Phase 6: 배포 테스트 (5분)

1. **수동 배포 테스트**
   ```bash
   ./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod E1XXXXXXXXXX
   ```

2. **자동 배포 테스트**
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```

3. **기능 테스트**
   - CloudFront URL 또는 도메인으로 접속
   - 모든 페이지 로딩 확인
   - API 통신 확인

---

## 필요한 AWS 권한 목록

### 초기 설정용 (관리자 또는 고급 권한)

- **S3**:
  - `s3:CreateBucket`
  - `s3:PutBucketPolicy`
  - `s3:PutBucketWebsite`
  - `s3:PutBucketCORS`

- **CloudFront**:
  - `cloudfront:CreateDistribution`
  - `cloudfront:CreateCloudFrontOriginAccessIdentity`
  - `cloudfront:UpdateDistribution`

- **ACM** (도메인 사용 시):
  - `acm:RequestCertificate`
  - `acm:DescribeCertificate`

- **Route 53** (도메인 사용 시):
  - `route53:ChangeResourceRecordSets`
  - `route53:ListHostedZones`

### 배포용 (GitHub Actions, 최소 권한)

- **S3**:
  - `s3:PutObject`
  - `s3:PutObjectAcl`
  - `s3:DeleteObject`
  - `s3:ListBucket`

- **CloudFront**:
  - `cloudfront:CreateInvalidation`
  - `cloudfront:GetDistribution`

상세 권한 정책: `github-actions-policy.json` 참조

---

## 예상 비용 정보

### 프리티어 (12개월, 신규 계정)

| 서비스 | 무료 제공량 |
|--------|------------|
| CloudFront | 50GB 데이터 전송/월, 2,000,000 요청/월 |
| S3 | 5GB 스토리지, 20,000 GET 요청/월 |
| ACM | 무료 (퍼블릭 인증서) |
| Route 53 | 없음 (항상 유료) |

### 프리티어 이후 예상 비용

#### 소규모 (월 1,000 사용자, 5GB 데이터 전송)
- **CloudFront**: $1.43
- **S3**: $0.01
- **Route 53**: $0.90 (도메인 사용 시)
- **총 비용**: **약 $1.44/월** (도메인 제외)
- **총 비용**: **약 $2.34/월** (도메인 포함)

#### 중규모 (월 10,000 사용자, 50GB 데이터 전송)
- **CloudFront**: $14.25
- **S3**: $0.01
- **Route 53**: $0.90 (도메인 사용 시)
- **총 비용**: **약 $14.26/월** (도메인 제외)
- **총 비용**: **약 $15.16/월** (도메인 포함)

#### 대규모 (월 100,000 사용자, 500GB 데이터 전송)
- **CloudFront**: $142.50
- **S3**: $0.01
- **Route 53**: $0.90 (도메인 사용 시)
- **총 비용**: **약 $142.51/월** (도메인 제외)
- **총 비용**: **약 $143.41/월** (도메인 포함)

### 비용 절감 팁
1. **Price Class 최적화**: PriceClass_100 사용 (40% 절감)
2. **압축 활성화**: Gzip/Brotli (70% 절감)
3. **캐싱 최적화**: TTL 길게 설정 (50% 절감)
4. **파일명 해시**: 캐시 무효화 비용 $0

상세 비용 분석: `AWS_COST_ESTIMATION.md` 참조

---

## 배포 후 확인사항

### 1. 기본 동작 확인
- [ ] CloudFront URL 접속 가능 (`https://d1234567890.cloudfront.net`)
- [ ] 도메인 접속 가능 (설정한 경우, `https://app.testcase.run`)
- [ ] HTTPS 리다이렉트 동작 (HTTP → HTTPS)
- [ ] 모든 페이지 로딩 정상

### 2. 기능 테스트
- [ ] SPA 라우팅 정상 (페이지 새로고침 시 404 없음)
- [ ] API 통신 정상 (`https://api.testcase.run/api`)
- [ ] Google OAuth 로그인 (설정된 경우)
- [ ] 코드 실행 및 테스트 기능

### 3. 성능 확인
- [ ] 페이지 로딩 속도 (목표: < 3초)
- [ ] CloudFront 캐시 히트율 (목표: > 90%)
- [ ] 브라우저 개발자 도구 > Network 탭 확인
  - [ ] `X-Cache: Hit from cloudfront` 헤더 확인
  - [ ] Gzip/Brotli 압축 확인

### 4. 보안 확인
- [ ] SSL 인증서 유효 (자물쇠 아이콘)
- [ ] Security Headers 확인
  - [ ] `Strict-Transport-Security`
  - [ ] `X-Content-Type-Options`
  - [ ] `X-Frame-Options`
- [ ] Mixed Content 경고 없음

### 5. 자동 배포 확인
- [ ] GitHub Actions 워크플로우 실행 성공
- [ ] S3 업로드 완료
- [ ] CloudFront 캐시 무효화 완료

---

## 문제 해결 참고

### 자주 발생하는 문제

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| 404 에러 | Custom Error Response 미설정 | CloudFront에서 403, 404 → `/index.html` 설정 |
| CORS 에러 | 백엔드 CORS 미설정 | Django `django-cors-headers` 설정 확인 |
| SSL 에러 | 인증서 리전 오류 | ACM 인증서를 us-east-1에서 발급 |
| Access Denied | S3 버킷 정책 오류 | OAI에 `s3:GetObject` 권한 부여 |
| 캐싱 문제 | CloudFront 캐시 | `aws cloudfront create-invalidation` 실행 |

상세 문제 해결: `AWS_CLOUDFRONT_DEPLOYMENT.md` > 7. 문제 해결 섹션 참조

---

## 다음 단계

### 운영 최적화
1. **모니터링 설정**
   - CloudWatch Alarms 설정
   - AWS Cost Explorer 활성화
   - 월별 예산 알림 설정

2. **보안 강화**
   - WAF (Web Application Firewall) 추가 (선택사항)
   - DDoS Protection (Shield Standard는 기본 포함)
   - Security Headers 추가 검토

3. **성능 최적화**
   - 이미지 최적화 (WebP, lazy loading)
   - 코드 스플리팅 검토
   - Lighthouse 점수 개선

### 추가 기능
1. **CI/CD 개선**
   - 스테이징 환경 추가
   - Blue-Green 배포
   - 롤백 자동화

2. **고급 기능**
   - Lambda@Edge (동적 콘텐츠 처리)
   - CloudFront Functions (간단한 로직)
   - S3 버전 관리

---

## 참고 자료

### 공식 문서
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)

### 커뮤니티
- [AWS Forums](https://forums.aws.amazon.com/)
- [Stack Overflow - AWS](https://stackoverflow.com/questions/tagged/amazon-web-services)
- [AWS re:Post](https://repost.aws/)

### 지원
- [AWS Support Center](https://console.aws.amazon.com/support)
- [AWS Service Health Dashboard](https://status.aws.amazon.com/)

---

## 작업 완료 체크리스트

- [x] 상세 배포 가이드 작성 (`AWS_CLOUDFRONT_DEPLOYMENT.md`)
- [x] 빠른 시작 가이드 작성 (`QUICKSTART_DEPLOYMENT.md`)
- [x] 배포 체크리스트 작성 (`DEPLOYMENT_CHECKLIST.md`)
- [x] GitHub Secrets 설정 가이드 작성 (`GITHUB_SECRETS_SETUP.md`)
- [x] AWS 권한 요구사항 문서 작성 (`AWS_PERMISSIONS_REQUIRED.md`)
- [x] 비용 예상 문서 작성 (`AWS_COST_ESTIMATION.md`)
- [x] GitHub Actions 워크플로우 작성 (`.github/workflows/deploy-cloudfront.yml`)
- [x] 배포 스크립트 작성 (`deploy-scripts/deploy-to-s3.sh`)
- [x] 설정 파일 작성 (S3 정책, CORS, CloudFront 무효화 등)
- [x] IAM 정책 파일 작성 (`github-actions-policy.json`)
- [x] CodeBuild 설정 작성 (`buildspec.yml`)
- [x] README 업데이트 (배포 섹션 추가)
- [x] 배포 요약 문서 작성 (이 문서)

---

## 마무리

AWS CloudFront를 사용한 프론트엔드 배포 가이드가 완성되었습니다. 이제 다음 단계로 진행하세요:

1. **빠른 시작**: `QUICKSTART_DEPLOYMENT.md` 참조
2. **상세 가이드**: `AWS_CLOUDFRONT_DEPLOYMENT.md` 참조
3. **자동 배포**: `GITHUB_SECRETS_SETUP.md` 참조

모든 파일은 프로젝트 루트에 위치하며, 언제든지 참조할 수 있습니다.

**Happy Deploying!**

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-10-06
**작성자**: Claude Code (Frontend Developer Agent)
