# Orphaned Job Recovery

## 문제 상황

Worker가 재시작되거나 crash되면 PROCESSING 상태의 job이 "orphaned" 상태로 남을 수 있습니다:
- Job은 PROCESSING 상태로 남아있음
- 하지만 실제로는 worker가 해당 작업을 처리하지 않음
- 사용자는 계속 진행 중인 것처럼 보이지만 실제로는 멈춰있음

## 해결 방법

### 1. Manual Recovery (즉시 복구)

Django management command를 사용하여 orphaned job을 수동으로 복구할 수 있습니다:

```bash
# Dry run: 어떤 job이 복구될지 미리 확인
docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 30 --dry-run

# 실제 복구 실행
docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 30
```

**Parameters:**
- `--timeout`: PROCESSING 상태로 이 시간(분) 이상 지난 job을 orphaned로 간주 (기본값: 30분)
- `--dry-run`: 실제로 변경하지 않고 무엇이 복구될지만 확인

**동작:**
1. `updated_at` 필드를 확인하여 timeout보다 오래된 PROCESSING job 찾기
2. 해당 job들을 FAILED 상태로 변경
3. Problem metadata 업데이트 (extraction job의 경우)
4. 복구 통계 출력

### 2. Automatic Recovery (주기적 자동 복구)

Celery Beat를 설정하여 주기적으로 자동 복구할 수 있습니다.

#### Celery Beat 설정 추가

`backend/config/celery.py` 또는 `backend/config/settings.py`에 다음 추가:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'recover-orphaned-jobs': {
        'task': 'api.tasks.recover_orphaned_jobs_task',
        'schedule': crontab(minute='*/15'),  # 15분마다 실행
        'kwargs': {'timeout_minutes': 30},  # 30분 timeout
    },
}
```

#### Celery Beat 실행

```bash
# Local development
celery -A config beat --loglevel=info

# Docker
docker exec algoitny-backend celery -A config beat --loglevel=info

# Docker Compose에 추가
services:
  celery-beat:
    image: algoitny-backend
    command: celery -A config beat --loglevel=info
    environment:
      - DB_HOST=mysql
      - REDIS_HOST=redis
    depends_on:
      - redis
      - mysql
```

### 3. API를 통한 수동 복구 (선택사항)

필요하다면 API endpoint를 추가할 수도 있습니다:

```python
# api/views/admin.py
class RecoverOrphanedJobsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from api.tasks import recover_orphaned_jobs_task
        result = recover_orphaned_jobs_task.delay(timeout_minutes=30)
        return Response({'task_id': result.id})
```

## 복구 후

복구된 job은 FAILED 상태가 되므로:
1. Frontend에서 retry 버튼이 표시됨
2. 사용자가 retry 버튼을 클릭하여 재시도 가능
3. 또는 API를 통해 프로그래밍 방식으로 재시도 가능

## 모니터링

### 로그 확인

```bash
# Management command 로그
docker logs algoitny-backend | grep "Orphaned Job Recovery"

# Celery task 로그
docker logs algoitny-celery-worker | grep "Orphaned Job Recovery"
```

### 메트릭

- `found_count`: 발견된 orphaned job 수
- `recovered_count`: 복구된 job 수
- `extraction_jobs`: 복구된 extraction job 수
- `generation_jobs`: 복구된 generation job 수
- `problems_updated`: 업데이트된 Problem 수

## Best Practices

1. **Timeout 설정**:
   - 너무 짧으면: 실제로 진행 중인 job도 orphaned로 간주될 수 있음
   - 너무 길면: orphaned job이 오래 방치됨
   - 권장값: 30분 (대부분의 extraction은 5-10분 내 완료)

2. **실행 주기**:
   - Celery Beat로 15분마다 실행 권장
   - 긴급한 경우 manual command로 즉시 실행

3. **알림 설정**:
   - Orphaned job이 발견되면 Slack/Email 알림 추가 고려
   - 자주 발생하면 worker 안정성 문제 조사 필요

## Troubleshooting

### Q: "No orphaned jobs found"가 나오는데 실제로는 있는 것 같아요
A: `--timeout` 값을 줄여보세요. 예: `--timeout 5`

### Q: 복구 후에도 계속 PROCESSING으로 나와요
A: Browser cache일 수 있습니다. 페이지를 새로고침하거나 hard refresh (Cmd+Shift+R)하세요.

### Q: Worker가 자주 crash되어 orphaned job이 많이 발생해요
A:
1. Worker 메모리 사용량 확인
2. Task timeout 설정 확인
3. Celery worker concurrency 설정 조정 고려
4. Worker 로그에서 crash 원인 분석

## 파일 위치

- Management command: `/backend/api/management/commands/recover_orphaned_jobs.py`
- Celery task: `/backend/api/tasks.py` (라인 1248-1357)
- Models: `/backend/api/models.py` (BaseJob.updated_at 사용)

## 예제

### 시나리오 1: Worker 재시작 후 즉시 복구

```bash
# Worker 재시작
docker restart algoitny-celery-worker

# 즉시 orphaned job 확인 및 복구 (5분 timeout)
docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 5
```

### 시나리오 2: 정기 점검

```bash
# 매일 점검 (cron에 추가)
0 */6 * * * docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 30
```

### 시나리오 3: Monitoring alert 후

```bash
# 알림을 받고 즉시 조사
docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 30 --dry-run

# 확인 후 복구
docker exec algoitny-backend python manage.py recover_orphaned_jobs --timeout 30
```
