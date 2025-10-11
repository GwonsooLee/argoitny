# Production Migration Guide: Plan Structure

## Overview

이 가이드는 Plan 데이터 구조를 Production 환경에서 안전하게 마이그레이션하는 방법을 설명합니다.

### 구조 변경 내용

**이전 구조:**
```
PK: PLAN#1,  SK: META
PK: PLAN#2,  SK: META
PK: PLAN#3,  SK: META
```

**새 구조:**
```
PK: PLAN,  SK: META#1
PK: PLAN,  SK: META#2
PK: PLAN,  SK: META#3
```

### 변경 이유
- ✅ Query 사용 (Scan보다 빠름)
- ✅ RCU 비용 절감
- ✅ 더 나은 DynamoDB 설계 패턴

---

## 📋 Pre-Migration Checklist

### 1. 환경 준비
```bash
# AWS 자격증명 확인
aws sts get-caller-identity

# 올바른 리전 확인
export AWS_DEFAULT_REGION=ap-northeast-2

# DynamoDB 테이블 접근 권한 확인
aws dynamodb describe-table --table-name algoitny_main
```

### 2. 백업 계획
- ✅ DynamoDB Point-in-Time Recovery 활성화 확인
- ✅ 마이그레이션 스크립트 자체 백업 생성
- ✅ 롤백 계획 준비

### 3. 점검 사항
- [ ] 현재 Plan 개수 확인 (3개 예상)
- [ ] 활성 사용자 수 확인
- [ ] 트래픽이 적은 시간대 선택
- [ ] 팀 전체 공지 완료

---

## 🚀 Migration Steps

### Step 1: Dry Run (안전 확인)

먼저 dry-run 모드로 실행하여 문제가 없는지 확인합니다.

```bash
cd /Users/gwonsoolee/algoitny/backend

# Dry run (기본값, 변경 없음)
python scripts/migrate_plan_structure_production.py --dry-run
```

**예상 출력:**
```
======================================================================
PRODUCTION PLAN STRUCTURE MIGRATION
======================================================================
Mode: DRY RUN
Table: algoitny_main
======================================================================
[INFO] Verifying old structure...
[SUCCESS] ✓ Found 3 plans with old structure
  - PLAN#1: Free
  - PLAN#2: Pro
  - PLAN#3: Admin
[INFO] Creating backup...
[SUCCESS] ✓ Backup saved: /path/to/backup.json
[INFO] [DRY RUN] Would create new structure item
...
[SUCCESS] ✓ DRY RUN completed successfully
```

### Step 2: Execute Migration

Dry run이 성공하면 실제 마이그레이션을 실행합니다.

```bash
# 실제 마이그레이션 실행
python scripts/migrate_plan_structure_production.py --execute
```

**확인 프롬프트:**
```
⚠ WARNING: This will modify production data!
Type 'MIGRATE' to continue: MIGRATE
```

**마이그레이션 프로세스:**
1. ✅ 기존 구조 확인
2. ✅ 백업 생성 (`backups/plan_backup_YYYYMMDD_HHMMSS.json`)
3. ✅ 새 구조로 아이템 생성
4. ✅ 기존 아이템 삭제
5. ✅ 검증 수행

### Step 3: Verification

마이그레이션 후 검증:

```bash
# 새 구조 확인
aws dynamodb query \
  --table-name algoitny_main \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{":pk": {"S": "PLAN"}, ":sk": {"S": "META#"}}' \
  --region ap-northeast-2

# API 테스트
curl -X GET "https://your-api.com/api/admin/plans/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 4: Application Deployment

마이그레이션 후 새 코드 배포:

```bash
# 백엔드 배포
git pull origin main
docker-compose restart backend

# 또는 ECS/EKS 배포
# kubectl rollout restart deployment/backend
```

---

## 🔄 Rollback Plan

만약 문제가 발생하면 백업으로 롤백할 수 있습니다.

### Option 1: 스크립트 롤백

```bash
# 백업 파일 경로 확인
ls -la backend/scripts/backups/

# 롤백 실행
python scripts/migrate_plan_structure_production.py \
  --rollback backend/scripts/backups/plan_backup_YYYYMMDD_HHMMSS.json
```

### Option 2: AWS Point-in-Time Recovery

```bash
# DynamoDB 콘솔에서 Point-in-Time Recovery 사용
# 또는 CLI로:
aws dynamodb restore-table-to-point-in-time \
  --source-table-name algoitny_main \
  --target-table-name algoitny_main_restored \
  --restore-date-time "2025-01-15T10:00:00Z"
```

### Option 3: 수동 롤백

백업 JSON 파일을 사용하여 수동 복구:

```python
import json
import boto3

# 백업 파일 로드
with open('plan_backup_YYYYMMDD_HHMMSS.json') as f:
    backup = json.load(f)

# DynamoDB에 복원
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('algoitny_main')

for plan in backup['plans']:
    table.put_item(Item=plan)
```

---

## 📊 Monitoring

마이그레이션 중/후 모니터링:

### DynamoDB 메트릭
```bash
# CloudWatch 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=algoitny_main \
  --start-time 2025-01-15T10:00:00Z \
  --end-time 2025-01-15T11:00:00Z \
  --period 300 \
  --statistics Sum
```

### 애플리케이션 로그
```bash
# ECS 로그
aws logs tail /aws/ecs/backend --follow

# 또는 kubectl
kubectl logs -f deployment/backend
```

---

## ⚠️ Important Notes

### 1. Downtime
- **예상 다운타임**: 없음 (무중단 마이그레이션)
- 새 구조와 기존 구조가 동시에 존재하는 짧은 시간 발생
- 읽기/쓰기 작업 모두 지원됨

### 2. 비용
- 마이그레이션 중 추가 WCU 사용 (일시적)
- 백업 저장 공간 (S3) 비용
- 마이그레이션 완료 후 RCU 비용 **절감**

### 3. 주의사항
- Plan 개수가 적어 빠르게 완료됨 (예상: 1초 이내)
- 마이그레이션 중 새로운 Plan 생성 피하기
- 백업 파일은 최소 30일 보관

---

## 🧪 Testing in Staging

Production 전에 Staging 환경에서 먼저 테스트:

```bash
# Staging 테이블로 테스트
export AWS_DEFAULT_REGION=ap-northeast-2
export DYNAMODB_TABLE=algoitny_staging

python scripts/migrate_plan_structure_production.py --execute
```

---

## 📞 Support

문제 발생 시:
1. 백업 파일 확보 확인
2. 롤백 스크립트 즉시 실행
3. CloudWatch 로그 확인
4. 팀에 에스컬레이션

---

## ✅ Post-Migration Checklist

- [ ] API 정상 작동 확인
- [ ] 모든 Plan 조회 가능 확인
- [ ] 사용자 Plan 할당 정상 확인
- [ ] CloudWatch 메트릭 정상 확인
- [ ] 백업 파일 안전한 위치에 보관
- [ ] 팀에 완료 공지
- [ ] 마이그레이션 문서 업데이트
