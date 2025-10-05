# Docker 이미지 최적화 가이드

## 최적화 내역

### 1. 불필요한 의존성 제거

#### Before:
```dockerfile
# Builder stage
RUN apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    default-jdk \              # ❌ 200-300MB
    default-libmysqlclient-dev \
    pkg-config

# Runtime stage
RUN apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    default-jdk \              # ❌ 200-300MB
    curl                       # ❌ 10MB
```

#### After:
```dockerfile
# Builder stage
RUN apt-get install -y --no-install-recommends \
    gcc \                      # ✅ g++ 제거
    default-libmysqlclient-dev \
    pkg-config

# Runtime stage
RUN apt-get install -y --no-install-recommends \
    libmariadb3               # ✅ 런타임 라이브러리만 설치
```

**절감량**: ~300-400MB

### 2. Python 패키지 정리

```dockerfile
RUN uv pip install --system -e . && \
    find /usr/local/lib/python3.12/site-packages -type d -name "tests" -exec rm -rf {} + && \
    find /usr/local/lib/python3.12/site-packages -type d -name "test" -exec rm -rf {} + && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyo" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "__pycache__" -type d -exec rm -rf {} +
```

- 테스트 파일 제거
- Bytecode 캐시 제거 (런타임에 자동 생성됨)

**절감량**: ~50-100MB

### 3. 바이너리 선택적 복사

#### Before:
```dockerfile
COPY --from=builder /usr/local/bin /usr/local/bin
```

#### After:
```dockerfile
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/celery /usr/local/bin/django-admin /usr/local/bin/
```

**절감량**: ~10-20MB

### 4. Health Check 최적화

#### Before:
```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/api/health/ || exit 1
```

#### After:
```dockerfile
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/').read()" || exit 1
```

- curl 제거로 이미지 크기 감소
- Python 표준 라이브러리 사용

### 5. .dockerignore 강화

추가된 항목:
```
__pycache__/
pip-log.txt
tests/
test_*.py
*_test.py
```

## 예상 효과

| 항목 | Before | After | 절감량 |
|------|--------|-------|--------|
| JDK | 300MB | 0MB | -300MB |
| MySQL 라이브러리 | 50MB | 10MB | -40MB |
| curl | 10MB | 0MB | -10MB |
| 테스트 파일 | 100MB | 0MB | -100MB |
| 불필요한 바이너리 | 20MB | 0MB | -20MB |
| **Total** | **~1.2GB** | **~750MB** | **~450MB (37% 감소)** |

## 빌드 및 확인

### 로컬 빌드
```bash
cd backend
docker build -t algoitny-backend:optimized .

# 이미지 크기 확인
docker images algoitny-backend:optimized
```

### 멀티 아키텍처 빌드
```bash
# 프로젝트 루트에서
git tag v0.0.2
make release
```

### 레이어 분석
```bash
# Docker Desktop 사용 시
# Image Inspect 기능으로 레이어별 크기 확인

# 또는 dive 사용 (설치 필요)
brew install dive
dive algoitny-backend:optimized
```

## 추가 최적화 고려사항

### 1. Alpine 이미지 사용 (고급)

현재 `python:3.12-slim` 사용 중 → `python:3.12-alpine`으로 변경 시 추가로 ~200MB 절감 가능

**주의사항**:
- mysqlclient 빌드가 복잡해짐 (musl 라이브러리 문제)
- 빌드 시간 증가 가능
- 일부 라이브러리 호환성 문제 가능

### 2. 정적 파일 외부화

현재 collectstatic을 이미지 빌드 시 수행 → S3 또는 CDN 사용 시 이미지에서 제외 가능

### 3. Multi-stage 더 공격적으로 활용

필요한 .so 파일만 선택적으로 복사

## 성능 영향

- **빌드 시간**: 큰 변화 없음 (오히려 약간 빠를 수 있음)
- **런타임 성능**: 영향 없음 (동일)
- **다운로드 시간**: 37% 감소 → Pod 시작 시간 단축
- **스토리지 비용**: ECR 저장 용량 감소

## 롤백 방법

문제 발생 시 이전 버전으로 롤백:
```bash
# Kubernetes
make k8s-rollback

# 또는 특정 태그로 배포
make deploy VERSION=v0.0.1
```
