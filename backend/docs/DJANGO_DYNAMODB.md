# Django DynamoDB Integration

Django 관련 모든 데이터를 DynamoDB에 저장하는 완전한 통합 구현입니다.

## 📋 개요

별도의 DynamoDB 테이블(`algoitny_django`)을 생성하여 Django 관련 데이터를 저장합니다:

- ✅ **Session 저장**: Django 세션을 DynamoDB에 저장
- ✅ **Celery Task Results**: 태스크 결과를 DynamoDB에 저장
- ✅ **TTL 자동 만료**: 만료된 데이터 자동 삭제
- ✅ **완전한 Async**: aioboto3 기반 비동기 구현

## 🗂️ 테이블 구조

### algoitny_django 테이블

```
Table Name: algoitny_django
Partition Key: PK (String)
Sort Key: SK (String)
Billing Mode: PAY_PER_REQUEST
TTL Attribute: exp (Number)

Global Secondary Index:
  - TypeIndex (tp, SK)
```

### 데이터 타입별 키 구조

#### 1. Session
```python
PK: SESSION#{session_key}
SK: META
tp: session
dat: "{...}"  # JSON serialized session data
exp: 1234567890  # TTL timestamp
crt: 1234567890
upd: 1234567890
```

#### 2. Celery Task Result
```python
PK: TASK#{task_id}
SK: META
tp: task_result
dat: "{...}"  # JSON serialized task result
exp: 1234567890  # TTL timestamp
crt: 1234567890
upd: 1234567890
```

## 🔧 설정

### Django Settings (`config/settings.py`)

```python
# Django DynamoDB 테이블
DJANGO_DYNAMODB_TABLE_NAME = 'algoitny_django'

# Session Backend
SESSION_ENGINE = 'api.sessions'
DYNAMODB_SESSION_TABLE_NAME = DJANGO_DYNAMODB_TABLE_NAME
SESSION_COOKIE_AGE = 3600  # 1 hour

# Celery Result Backend
USE_CELERY_RESULT_BACKEND = True
CELERY_RESULT_BACKEND = 'api.celery_backends.dynamodb.DynamoDBBackend'
CELERY_RESULT_EXPIRES = 86400  # 24 hours
```

### 환경 변수

```bash
# LocalStack (개발)
LOCALSTACK_URL=http://localhost:4566
DJANGO_DYNAMODB_TABLE_NAME=algoitny_django

# Production (AWS)
DJANGO_DYNAMODB_TABLE_NAME=algoitny_django
AWS_DEFAULT_REGION=ap-northeast-2
```

## 📦 구현된 컴포넌트

### 1. Session Backend

**위치**: `backend/api/sessions/dynamodb.py`

```python
# Async 사용
from api.sessions.dynamodb import AsyncDynamoDBSessionStore

async def my_view(request):
    session = AsyncDynamoDBSessionStore(session_key)
    data = await session.load()

# Sync 사용 (Django middleware)
from api.sessions.dynamodb import DynamoDBSessionStore

def my_view(request):
    # request.session 자동으로 DynamoDB 사용
    request.session['user_id'] = 123
```

**특징**:
- ✅ 완전한 async 구현 (aioboto3)
- ✅ Django middleware 호환 (sync wrapper)
- ✅ TTL 자동 만료
- ✅ JSON 직렬화

### 2. Celery Result Backend

**위치**: `backend/api/celery_backends/dynamodb.py`

```python
from api.celery_backends.dynamodb import DynamoDBBackend

# Celery 자동으로 사용
@celery_app.task
def my_task():
    return {"result": "success"}

# 결과 조회
result = my_task.delay()
print(result.get())  # DynamoDB에서 자동으로 조회
```

**특징**:
- ✅ Celery BaseBackend 구현
- ✅ Async DynamoDB 연동
- ✅ 태스크 상태 추적 (SUCCESS, FAILURE, PENDING, etc.)
- ✅ Traceback 저장 (실패 시)

## 🚀 초기 설정

### 1. DynamoDB 테이블 생성

```bash
# LocalStack (개발)
cd backend
LOCALSTACK_URL=http://localhost:4566 python scripts/init_django_dynamodb.py

# Production (AWS)
python scripts/init_django_dynamodb.py
```

**출력 예시**:
```
============================================================
Django DynamoDB Table Initialization
============================================================
Using LocalStack at http://localhost:4566

Creating table: algoitny_django...
✓ Table 'algoitny_django' created successfully!

Table structure:
  - Partition Key: PK (String)
  - Sort Key: SK (String)
  - GSI: TypeIndex (tp, SK)
  - Billing: PAY_PER_REQUEST

✓ TTL enabled for automatic data expiration
✓ Table is ready for use
```

### 2. TTL 활성화 (자동 실행됨)

TTL은 테이블 생성 시 자동으로 활성화됩니다:
- Session: `SESSION_COOKIE_AGE` (기본 1시간)
- Task Result: `CELERY_RESULT_EXPIRES` (기본 24시간)

## 🧪 테스트

### Session Backend 테스트

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings LOCALSTACK_URL=http://localhost:4566 \
python scripts/test_session_backend.py
```

**테스트 항목**:
- ✅ 세션 생성/저장/로드
- ✅ 세션 만료 처리
- ✅ 세션 삭제
- ✅ Async/Sync 모두 테스트

### Celery Backend 테스트

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings LOCALSTACK_URL=http://localhost:4566 \
python scripts/test_celery_backend.py
```

**테스트 항목**:
- ✅ 성공 태스크 결과 저장/조회
- ✅ 실패 태스크 결과 저장/조회 (traceback 포함)
- ✅ 존재하지 않는 태스크 조회
- ✅ 결과 삭제 (forget)

## 📊 데이터 확인

### DynamoDB 테이블 내용 조회

```bash
cd backend
LOCALSTACK_URL=http://localhost:4566 python -c "
import boto3

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:4566',
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

table = dynamodb.Table('algoitny_django')
response = table.scan()
items = response.get('Items', [])

print(f'Total items: {len(items)}')
for item in items:
    print(f\"Type: {item.get('tp'):15} | PK: {item.get('PK')}\")
"
```

**출력 예시**:
```
Total items: 3
Type: session         | PK: SESSION#abc123...
Type: task_result     | PK: TASK#task-456...
Type: session         | PK: SESSION#test-session-key-123
```

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────┐
│           Django Application            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │   Sessions   │  │  Celery Tasks   │ │
│  │  (Sync/Async)│  │   (Results)     │ │
│  └──────┬───────┘  └────────┬────────┘ │
│         │                    │          │
│         ▼                    ▼          │
│  ┌─────────────────────────────────┐   │
│  │  DynamoDB Session/Result Stores │   │
│  │         (aioboto3)              │   │
│  └────────────────┬────────────────┘   │
└───────────────────┼─────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  algoitny_django      │
        │  DynamoDB Table       │
        ├───────────────────────┤
        │  • Sessions           │
        │  • Task Results       │
        │  • TTL Auto-Cleanup   │
        └───────────────────────┘
```

## 🎯 사용 사례

### 1. API View에서 Session 사용

```python
from adrf.views import APIView

class MyView(APIView):
    async def get(self, request):
        # Session 자동으로 DynamoDB 사용
        user_id = request.session.get('user_id')

        # Session 저장
        request.session['last_visit'] = datetime.now()

        return Response({'user_id': user_id})
```

### 2. Celery Task 결과 확인

```python
from celery import current_app

@current_app.task
def process_data(data):
    # 처리 로직
    result = {"processed": len(data)}
    return result  # DynamoDB에 자동 저장

# Task 실행 및 결과 조회
task = process_data.delay([1, 2, 3])
print(task.state)    # PENDING, SUCCESS, etc.
print(task.result)   # DynamoDB에서 조회
```

### 3. Manual Session 관리

```python
from api.sessions.dynamodb import AsyncDynamoDBSessionStore

async def custom_session_logic():
    # 새 세션 생성
    session = AsyncDynamoDBSessionStore()
    await session.create()

    # 데이터 저장
    session._session_cache = {
        'user_id': 123,
        'permissions': ['read', 'write']
    }
    await session.save()

    # 세션 로드
    loaded = AsyncDynamoDBSessionStore(session.session_key)
    data = await loaded.load()
    print(data)  # {'user_id': 123, 'permissions': [...]}
```

## ⚙️ 설정 옵션

### Session 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `SESSION_ENGINE` | `api.sessions` | Session backend 엔진 |
| `DYNAMODB_SESSION_TABLE_NAME` | `algoitny_django` | Session 테이블명 |
| `SESSION_COOKIE_AGE` | `3600` | Session 만료 시간 (초) |
| `SESSION_SAVE_EVERY_REQUEST` | `False` | 매 요청마다 저장 여부 |

### Celery Backend 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `USE_CELERY_RESULT_BACKEND` | `True` | Result backend 사용 여부 |
| `CELERY_RESULT_BACKEND` | `api.celery_backends.dynamodb.DynamoDBBackend` | Backend 클래스 |
| `CELERY_RESULT_EXPIRES` | `86400` | 결과 만료 시간 (초) |
| `DJANGO_DYNAMODB_TABLE_NAME` | `algoitny_django` | DynamoDB 테이블명 |

## 🔒 보안 고려사항

1. **Session 보안**
   - `SESSION_COOKIE_SECURE = True` (HTTPS)
   - `SESSION_COOKIE_HTTPONLY = True`
   - `SESSION_COOKIE_SAMESITE = 'Lax'`

2. **DynamoDB 접근**
   - Production: IAM 역할 사용
   - Development: LocalStack 테스트 자격증명

3. **데이터 암호화**
   - DynamoDB at-rest 암호화 활성화 (Production)
   - 민감한 세션 데이터는 추가 암호화 고려

## 📈 성능 최적화

1. **TTL 활용**
   - 자동 만료로 수동 cleanup 불필요
   - Write capacity 절약

2. **Async I/O**
   - aioboto3 기반 비동기 처리
   - Event loop 블로킹 없음

3. **Pay-per-Request**
   - 사용량에 따른 과금
   - Auto-scaling

4. **GSI 활용**
   - TypeIndex로 타입별 효율적 조회
   - 필요시 추가 GSI 생성 가능

## 🐛 트러블슈팅

### Session이 저장되지 않음

```bash
# TTL 상태 확인
aws dynamodb describe-time-to-live \
    --table-name algoitny_django \
    --endpoint-url http://localhost:4566

# Session 데이터 확인
LOCALSTACK_URL=http://localhost:4566 python scripts/test_session_backend.py
```

### Celery 결과 조회 실패

```python
# Backend 설정 확인
from django.conf import settings
print(settings.CELERY_RESULT_BACKEND)
print(settings.DJANGO_DYNAMODB_TABLE_NAME)

# 수동 테스트
python scripts/test_celery_backend.py
```

### 테이블이 없음

```bash
# 테이블 재생성
LOCALSTACK_URL=http://localhost:4566 python scripts/init_django_dynamodb.py
```

## 📚 관련 문서

- [Session Backend 구현](../api/sessions/dynamodb.py)
- [Celery Backend 구현](../api/celery_backends/dynamodb.py)
- [테이블 초기화 스크립트](../scripts/init_django_dynamodb.py)
- [Django Settings](../config/settings.py)

## ✅ 체크리스트

배포 전 확인사항:

- [ ] DynamoDB 테이블 생성됨
- [ ] TTL 활성화됨
- [ ] Session backend 테스트 통과
- [ ] Celery backend 테스트 통과
- [ ] 서버 정상 시작
- [ ] Production 설정 확인 (IAM, 암호화)
- [ ] 모니터링 설정 (CloudWatch)
- [ ] 비용 알림 설정

## 🎉 마이그레이션 완료!

이제 모든 Django 관련 데이터가 DynamoDB에 저장됩니다:

```bash
# 기존: SQLite + Cache
django.contrib.sessions.backends.cache → LocMemCache

# 현재: DynamoDB
api.sessions → algoitny_django (TTL, Async)
api.celery_backends.dynamodb → algoitny_django (TTL, Async)
```

**장점**:
- ✅ 완전한 서버리스 아키텍처
- ✅ 자동 확장 및 고가용성
- ✅ TTL 기반 자동 cleanup
- ✅ Async/Await 완벽 지원
- ✅ 별도 Redis/Memcached 불필요
