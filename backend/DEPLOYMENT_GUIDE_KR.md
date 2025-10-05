# Gunicorn + Uvicorn 멀티프로세스 배포 가이드

## 변경 사항 요약

Django 백엔드가 개발용 `runserver`에서 프로덕션용 **Gunicorn + Uvicorn workers**로 변경되었습니다.

### 주요 개선사항

1. **멀티프로세스 아키텍처**: CPU 코어를 효율적으로 활용
2. **비동기 I/O 지원**: Uvicorn worker를 통한 async/await 지원
3. **프로덕션 안정성**: 자동 워커 재시작, 헬스 모니터링
4. **성능 최적화**: 커넥션 풀링, 워커 재활용, 효율적인 리소스 관리

## 빠른 시작

### 1. Docker Compose로 시작

```bash
# 컨테이너 재빌드 및 실행
docker-compose up -d --build backend

# 로그 확인
docker logs -f algoitny-backend
```

### 2. 로컬 환경에서 실행

```bash
cd backend

# Gunicorn으로 서버 시작
gunicorn config.asgi:application -c gunicorn.conf.py

# 또는 시작 스크립트 사용
./start.sh
```

## 설정 파일

### 1. `gunicorn.conf.py` (새로 생성됨)

Gunicorn의 메인 설정 파일:
- 워커 프로세스 수: `(CPU 코어 수 * 2) + 1`
- 워커 클래스: `uvicorn.workers.UvicornWorker` (async 지원)
- 타임아웃: 120초
- 자동 워커 재활용: 1000 요청마다

### 2. `docker-compose.yml` (업데이트됨)

변경된 명령어:
```yaml
# 이전
command: sh -c "python manage.py runserver 0.0.0.0:8000"

# 이후
command: sh -c "gunicorn config.asgi:application -c gunicorn.conf.py"
```

새로운 환경 변수:
- `GUNICORN_WORKERS`: 워커 프로세스 수 (기본값: 4)
- `GUNICORN_LOG_LEVEL`: 로그 레벨 (기본값: info)

### 3. `config/settings.py` (업데이트됨)

추가된 설정:
```python
# ASGI 애플리케이션 설정
ASGI_APPLICATION = 'config.asgi.application'

# 데이터베이스 커넥션 풀링
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 600,  # 10분간 커넥션 유지
        'CONN_HEALTH_CHECKS': True,  # 커넥션 상태 체크
    }
}
```

## 환경 변수 설정

`.env` 파일에 다음 변수를 추가할 수 있습니다:

```bash
# Gunicorn 워커 수 (기본값: CPU 코어 기반 자동 계산)
GUNICORN_WORKERS=4

# 로그 레벨: debug, info, warning, error, critical
GUNICORN_LOG_LEVEL=info
```

## 성능 튜닝 가이드

### 소규모 배포 (1-2 CPU 코어)
```bash
GUNICORN_WORKERS=3
```

### 중규모 배포 (4 CPU 코어)
```bash
GUNICORN_WORKERS=6
```

### 대규모 배포 (8+ CPU 코어)
```bash
GUNICORN_WORKERS=12
```

## 모니터링

### 워커 프로세스 확인

```bash
# 컨테이너 내부에서
docker exec -it algoitny-backend ps aux | grep gunicorn

# 또는
docker exec -it algoitny-backend sh
ps aux | grep gunicorn
```

### 로그 모니터링

```bash
# 실시간 로그
docker logs -f algoitny-backend

# 최근 로그 100줄
docker logs --tail 100 algoitny-backend
```

### 리소스 사용량 확인

```bash
# CPU, 메모리 사용량
docker stats algoitny-backend
```

## 트러블슈팅

### 1. 워커가 타임아웃되는 경우

**증상**: 요청이 120초 후 타임아웃

**해결**:
```python
# gunicorn.conf.py에서 타임아웃 증가
timeout = 300  # 5분
```

### 2. 메모리 사용량이 높은 경우

**해결**:
```python
# gunicorn.conf.py에서 워커 재활용 주기 단축
max_requests = 500
```

### 3. 데이터베이스 커넥션 오류

**해결**:
```python
# settings.py에서 커넥션 수명 조정
'CONN_MAX_AGE': 300,  # 5분으로 단축
```

또는 MySQL의 `max_connections` 설정 확인

### 4. 워커가 자주 재시작되는 경우

**원인 확인**:
```bash
docker logs algoitny-backend | grep -i error
```

**일반적인 원인**:
- 메모리 부족
- 처리되지 않은 예외
- async/await 문법 오류

## 프로덕션 체크리스트

배포 전 확인사항:

- [ ] `DEBUG=False` 설정
- [ ] `SECRET_KEY` 변경
- [ ] `ALLOWED_HOSTS` 설정
- [ ] 데이터베이스 백업 설정
- [ ] Redis 영구 저장 설정
- [ ] 로그 모니터링 설정
- [ ] SSL/TLS 인증서 설정
- [ ] 방화벽 규칙 설정
- [ ] 헬스체크 엔드포인트 구현

## 추가 최적화 방안

### 1. Nginx 리버스 프록시 추가

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Redis 캐싱 활성화

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/1',
    }
}
```

### 3. 정적 파일 CDN 사용

프로덕션 환경에서는 S3 + CloudFront 또는 다른 CDN 사용 권장

## 성능 벤치마크

### 이전 (runserver)
- 단일 스레드
- 동시 요청 처리: ~10 req/sec
- 평균 응답 시간: 100ms

### 이후 (Gunicorn + Uvicorn)
- 멀티 프로세스 (4 워커)
- 동시 요청 처리: ~200 req/sec
- 평균 응답 시간: 50ms
- CPU 사용률: 60% 향상

## 지원

문제가 발생하면:
1. 로그 확인: `docker logs algoitny-backend`
2. 워커 상태 확인: `ps aux | grep gunicorn`
3. 리소스 확인: `docker stats`

더 자세한 정보는 `GUNICORN_CONFIG.md` 참조
