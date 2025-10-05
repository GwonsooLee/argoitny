# AWS CloudFront 배포 비용 예상

AWS CloudFront와 S3를 사용한 프론트엔드 배포의 예상 비용을 상세하게 분석합니다.

## 목차
1. [비용 구성 요소](#1-비용-구성-요소)
2. [사용량 시나리오별 비용](#2-사용량-시나리오별-비용)
3. [AWS 프리티어](#3-aws-프리티어)
4. [비용 절감 방법](#4-비용-절감-방법)
5. [비용 모니터링](#5-비용-모니터링)
6. [비용 최적화 체크리스트](#6-비용-최적화-체크리스트)

---

## 1. 비용 구성 요소

### 1.1 Amazon S3

#### 스토리지 비용
- **Standard Storage**: $0.023/GB/월 (처음 50TB)
- 예상 빌드 크기: 약 5MB (React + Vite)
- **월 비용**: **$0.0001** (거의 무료)

#### 요청 비용
- **PUT/POST 요청**: $0.005/1,000 요청
- **GET/SELECT 요청**: $0.0004/1,000 요청
- CloudFront OAI 사용 시 S3 요청은 CloudFront만 수행
- **월 비용**: **$0.01 미만** (무시 가능)

#### 데이터 전송 비용
- CloudFront에서 S3로 가져가는 데이터 전송은 **무료**
- S3에서 인터넷으로의 직접 전송 없음 (CloudFront 사용)
- **월 비용**: **$0**

**S3 총 월 비용**: **약 $0.01**

---

### 1.2 Amazon CloudFront

#### 데이터 전송 비용 (미국/유럽 기준)

| 데이터 전송량 | 가격 (GB당) |
|--------------|------------|
| 처음 10TB/월 | $0.085 |
| 다음 40TB/월 | $0.080 |
| 다음 100TB/월 | $0.060 |
| 다음 350TB/월 | $0.040 |
| 500TB 초과 | $0.030 |

**리전별 가격 차이**:
- **미국/유럽**: $0.085/GB
- **아시아 (한국, 일본)**: $0.140/GB
- **인도**: $0.170/GB
- **남미**: $0.250/GB

#### HTTP/HTTPS 요청 비용

| 요청 타입 | 가격 (10,000 요청당) |
|----------|---------------------|
| HTTP | $0.0075 |
| HTTPS | $0.010 |

#### 캐시 무효화 비용
- **처음 1,000 경로/월**: 무료
- **1,000 경로 초과**: $0.005/경로

**CloudFront 기본 비용 (소규모)**:
- 데이터 전송: 5GB × $0.085 = **$0.43**
- HTTPS 요청: 100,000 요청 × $0.010 = **$1.00**
- 캐시 무효화: 무료 (1,000 경로 이내)
- **총 월 비용**: **약 $1.43**

---

### 1.3 AWS Certificate Manager (ACM)

- **퍼블릭 SSL/TLS 인증서**: **무료**
- 도메인 검증: **무료**
- 자동 갱신: **무료**

**ACM 월 비용**: **$0**

---

### 1.4 Amazon Route 53 (도메인 사용 시)

#### Hosted Zone 비용
- **1개 Hosted Zone**: $0.50/월
- **추가 Hosted Zone**: $0.50/월

#### 쿼리 비용

| 쿼리 수 | 가격 (백만 쿼리당) |
|---------|------------------|
| 처음 10억 쿼리/월 | $0.40 |
| 10억 쿼리 초과 | $0.20 |

**예상 쿼리**: 월 1,000,000 쿼리 = **$0.40**

**Route 53 월 비용** (도메인 사용 시):
- Hosted Zone: $0.50
- 쿼리: $0.40
- **총 월 비용**: **약 $0.90**

---

### 1.5 CloudWatch (모니터링)

#### 기본 모니터링
- CloudFront 기본 메트릭: **무료**
- S3 기본 메트릭: **무료**

#### 상세 모니터링 (선택사항)
- 커스텀 메트릭: $0.30/메트릭/월
- 로그 저장: $0.50/GB/월
- 로그 수집: $0.50/GB

**CloudWatch 월 비용** (기본): **$0**

---

## 2. 사용량 시나리오별 비용

### 2.1 소규모 (월 1,000 사용자)

**가정**:
- 사용자당 페이지 뷰: 5회
- 페이지당 크기: 1MB (초기 로드)
- 총 데이터 전송: 5GB
- 총 HTTPS 요청: 100,000회
- CloudFront 캐시 히트율: 90%

**비용 분석**:
| 서비스 | 월 비용 |
|--------|---------|
| S3 | $0.01 |
| CloudFront (데이터 전송) | $0.43 |
| CloudFront (HTTPS 요청) | $1.00 |
| ACM | $0.00 |
| **총 비용** | **$1.44** |

**Route 53 포함 시**: **$2.34**

---

### 2.2 중규모 (월 10,000 사용자)

**가정**:
- 사용자당 페이지 뷰: 5회
- 페이지당 크기: 1MB
- 총 데이터 전송: 50GB
- 총 HTTPS 요청: 1,000,000회
- CloudFront 캐시 히트율: 90%

**비용 분석**:
| 서비스 | 월 비용 |
|--------|---------|
| S3 | $0.01 |
| CloudFront (데이터 전송) | $4.25 |
| CloudFront (HTTPS 요청) | $10.00 |
| ACM | $0.00 |
| **총 비용** | **$14.26** |

**Route 53 포함 시**: **$15.16**

---

### 2.3 대규모 (월 100,000 사용자)

**가정**:
- 사용자당 페이지 뷰: 5회
- 페이지당 크기: 1MB
- 총 데이터 전송: 500GB
- 총 HTTPS 요청: 10,000,000회
- CloudFront 캐시 히트율: 95%

**비용 분석**:
| 서비스 | 월 비용 |
|--------|---------|
| S3 | $0.01 |
| CloudFront (데이터 전송) | $42.50 |
| CloudFront (HTTPS 요청) | $100.00 |
| ACM | $0.00 |
| **총 비용** | **$142.51** |

**Route 53 포함 시**: **$143.41**

---

### 2.4 최소 사용 (개발/테스트)

**가정**:
- 월 데이터 전송: 1GB
- 월 HTTPS 요청: 10,000회

**비용 분석**:
| 서비스 | 월 비용 |
|--------|---------|
| S3 | $0.01 |
| CloudFront (데이터 전송) | $0.09 |
| CloudFront (HTTPS 요청) | $0.10 |
| ACM | $0.00 |
| **총 비용** | **$0.20** |

---

## 3. AWS 프리티어

### 3.1 신규 AWS 계정 혜택 (12개월)

#### CloudFront
- **데이터 전송**: 50GB/월 무료 (전 세계)
- **HTTP/HTTPS 요청**: 2,000,000 요청/월 무료
- **유효 기간**: 계정 생성 후 12개월

#### S3
- **Standard Storage**: 5GB 무료
- **PUT/POST 요청**: 2,000 요청/월 무료
- **GET 요청**: 20,000 요청/월 무료
- **데이터 전송**: 15GB/월 무료 (아웃바운드)
- **유효 기간**: 계정 생성 후 12개월

#### Route 53
- **프리티어 없음** (항상 유료)

### 3.2 프리티어 적용 시 비용

**소규모 (월 1,000 사용자)** - 프리티어 12개월:
- 데이터 전송 5GB < 50GB 무료 → **$0**
- HTTPS 요청 100,000 < 2,000,000 무료 → **$0**
- S3 스토리지 5MB < 5GB 무료 → **$0**
- **총 비용**: **$0** (Route 53 제외)

**중규모 (월 10,000 사용자)** - 프리티어 12개월:
- 데이터 전송 50GB - 50GB 무료 = 0GB → **$0**
- HTTPS 요청 1,000,000 < 2,000,000 무료 → **$0**
- **총 비용**: **$0** (Route 53 제외)

**프리티어는 12개월 후 만료되며, 이후 일반 요금 부과**

---

## 4. 비용 절감 방법

### 4.1 CloudFront 최적화

#### 1) Price Class 선택
- **PriceClass_100**: 미국, 캐나다, 유럽만 (가장 저렴)
- **PriceClass_200**: PriceClass_100 + 아시아 (일본, 한국, 싱가포르 등)
- **PriceClass_All**: 전 세계 (가장 비쌈)

**비용 차이**:
- PriceClass_100: $0.085/GB (미국/유럽)
- PriceClass_All: $0.140/GB (아시아 포함)
- **절감**: 약 40%

**설정 방법**:
```json
{
  "PriceClass": "PriceClass_100"
}
```

#### 2) 캐싱 정책 최적화
- TTL을 길게 설정 (예: 1년)
- 정적 자산 캐싱 극대화
- `Cache-Control: max-age=31536000, immutable`

**효과**:
- Origin 요청 감소
- CloudFront 캐시 히트율 증가 (90% → 95%)
- **절감**: 요청 비용 약 50% 감소

#### 3) 압축 활성화
- Gzip/Brotli 압축 활성화
- 전송 데이터 크기 감소 (평균 60-70%)

**효과**:
- 1MB 파일 → 300KB (70% 감소)
- **절감**: 데이터 전송 비용 약 70% 감소

### 4.2 S3 최적화

#### 1) Lifecycle Policy
- 오래된 빌드 파일 자동 삭제
- Intelligent-Tiering 사용 (접근 빈도에 따라 자동 이동)

```bash
# Lifecycle 정책 예시
aws s3api put-bucket-lifecycle-configuration \
  --bucket algoitny-frontend-prod \
  --lifecycle-configuration file://lifecycle.json
```

#### 2) S3 Transfer Acceleration 비활성화
- CloudFront 사용 시 불필요
- 추가 비용 발생 없음

### 4.3 캐시 무효화 최적화

#### 1) 경로 최소화
- 전체 무효화 (`/*`) 대신 특정 경로만 무효화
- 예: `/index.html`, `/assets/app.*.js`

**비용 차이**:
- 전체 무효화: 1 경로 (무료)
- 특정 파일 5개: 5 경로 (무료, 1,000 경로 이내)

#### 2) 버전 관리
- 파일 이름에 해시 포함 (Vite 기본 동작)
- 예: `app.abc123.js`
- 캐시 무효화 불필요 (새 파일명이므로)

**효과**:
- 캐시 무효화 비용 **$0**
- 배포 속도 향상

### 4.4 기타 절감 방법

#### 1) Reserved Capacity (장기 약정)
- CloudFront Dedicated IP는 비용 발생
- 표준 CloudFront는 약정 불필요

#### 2) 모니터링 최적화
- 기본 CloudWatch 메트릭 사용 (무료)
- 상세 모니터링은 필요 시에만 활성화

#### 3) 로그 저장 최적화
- CloudFront 로그는 S3에 저장
- S3 Lifecycle로 오래된 로그 자동 삭제
- 예: 30일 후 삭제 또는 Glacier로 이동

---

## 5. 비용 모니터링

### 5.1 AWS Cost Explorer

#### 설정 방법
1. AWS Console > Cost Explorer 접속
2. "Enable Cost Explorer" 클릭
3. 비용 보고서 생성

#### 유용한 필터
- **서비스별**: CloudFront, S3, Route 53
- **태그별**: Environment=production
- **기간별**: 월별, 일별

#### 예산 알림 설정
```bash
# AWS Budgets 생성
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json
```

**budget.json**:
```json
{
  "BudgetName": "Algoitny-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "10",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### 5.2 CloudWatch 메트릭

#### 모니터링할 메트릭
- **CloudFront**: Requests, BytesDownloaded, BytesUploaded
- **S3**: BucketSizeBytes, NumberOfObjects

#### 알림 설정
```bash
# CloudWatch Alarm 생성
aws cloudwatch put-metric-alarm \
  --alarm-name high-cloudfront-requests \
  --alarm-description "Alert when CloudFront requests exceed 1M" \
  --metric-name Requests \
  --namespace AWS/CloudFront \
  --statistic Sum \
  --period 86400 \
  --threshold 1000000 \
  --comparison-operator GreaterThanThreshold
```

### 5.3 비용 분석 도구

#### AWS CLI로 비용 확인
```bash
# 월별 CloudFront 비용
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-02-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --filter file://cloudfront-filter.json
```

#### 서드파티 도구
- **CloudHealth**: 비용 최적화 추천
- **Cloudability**: 비용 분석 및 예측
- **AWS Cost Anomaly Detection**: 비정상 비용 감지

---

## 6. 비용 최적화 체크리스트

### 초기 설정
- [ ] CloudFront Price Class를 PriceClass_100으로 설정
- [ ] Gzip/Brotli 압축 활성화
- [ ] S3 버킷을 Private으로 설정 (CloudFront OAI만 접근)
- [ ] CloudFront Default TTL을 길게 설정 (86400초 이상)

### 배포 프로세스
- [ ] 정적 자산 파일명에 해시 포함 (Vite 기본)
- [ ] `index.html`만 캐시 무효화 (`Cache-Control: max-age=0`)
- [ ] 기타 파일은 장기 캐싱 (`Cache-Control: max-age=31536000`)
- [ ] 배포 스크립트에서 불필요한 파일 제외

### 운영
- [ ] AWS Cost Explorer 활성화
- [ ] 월별 예산 알림 설정 ($10, $50, $100 등)
- [ ] CloudFront 캐시 히트율 모니터링 (목표: 90% 이상)
- [ ] 오래된 S3 빌드 파일 자동 삭제 (Lifecycle Policy)

### 정기 점검 (월별)
- [ ] Cost Explorer에서 비용 추세 확인
- [ ] CloudFront 사용량 리포트 검토
- [ ] 불필요한 리소스 정리 (미사용 Distribution, 버킷 등)
- [ ] 캐시 무효화 횟수 확인 (1,000 경로 이내 유지)

---

## 7. 비용 예측 계산기

### 온라인 계산기
- **AWS Pricing Calculator**: https://calculator.aws/
- CloudFront, S3, Route 53 비용 정확히 계산

### 예상 월 비용 공식

#### 소규모 애플리케이션
```
월 사용자: 1,000명
월 페이지 뷰: 5,000회
평균 페이지 크기: 1MB
월 데이터 전송: 5GB

CloudFront 비용 = (5GB × $0.085) + (100,000 요청 × $0.00001)
                = $0.425 + $1.00
                = $1.43

S3 비용 = 거의 무료 ($0.01)

총 비용 = $1.44/월
```

#### 중규모 애플리케이션
```
월 사용자: 10,000명
월 데이터 전송: 50GB

CloudFront 비용 = (50GB × $0.085) + (1,000,000 요청 × $0.00001)
                = $4.25 + $10.00
                = $14.25

총 비용 = $14.26/월
```

---

## 8. 요약

### 예상 월 비용

| 규모 | 사용자 수 | 데이터 전송 | 월 비용 (도메인 제외) | 월 비용 (도메인 포함) |
|------|----------|------------|---------------------|---------------------|
| 최소 | 개발/테스트 | 1GB | $0.20 | $1.10 |
| 소규모 | 1,000 | 5GB | $1.44 | $2.34 |
| 중규모 | 10,000 | 50GB | $14.26 | $15.16 |
| 대규모 | 100,000 | 500GB | $142.51 | $143.41 |

### 프리티어 (12개월)
- **소규모**: **무료** (Route 53 제외)
- **중규모**: **무료** (50GB 이내, Route 53 제외)

### 비용 절감 팁
1. Price Class를 PriceClass_100 사용 (**40% 절감**)
2. 압축 활성화 (**70% 절감**)
3. 캐싱 최적화 (**50% 절감**)
4. 파일명 해시 사용 (무효화 비용 **$0**)

### 예산 추천
- **개발/테스트**: $5/월
- **소규모 프로덕션**: $10/월
- **중규모**: $20/월
- **대규모**: $200/월

---

**비용을 절감하면서도 높은 성능을 유지할 수 있습니다!**
