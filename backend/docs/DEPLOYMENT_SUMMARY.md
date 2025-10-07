# AWS EC2 Django Deployment - Summary Report

## 생성된 파일 목록

### 1. 배포 가이드 및 문서
- **`AWS_EC2_DEPLOYMENT.md`** - 상세한 EC2 배포 가이드 (완전한 단계별 설명)
- **`DEPLOYMENT_CHECKLIST.md`** - 배포 전/후 체크리스트
- **`DEPLOYMENT_SUMMARY.md`** - 이 파일 (배포 요약)

### 2. 배포 스크립트
- **`deploy-scripts/setup-ec2.sh`** - EC2 초기 설정 자동화 스크립트
  - 시스템 패키지 설치
  - Python 3.11, MySQL, Redis, Nginx 설치
  - 보안 설정 (UFW, Fail2Ban, SSH hardening)
  - 디렉토리 구조 생성
- **`deploy-scripts/deploy.sh`** - 애플리케이션 배포/업데이트 스크립트
  - Git pull
  - 의존성 업데이트
  - 마이그레이션
  - 서비스 재시작

### 3. Systemd 서비스 파일
- **`systemd/gunicorn.service`** - Gunicorn WSGI 서버
  - 4 workers (t3.medium 기준)
  - Unix socket 통신
  - 자동 재시작
- **`systemd/celery-worker.service`** - Celery 비동기 작업 워커
  - 4 concurrency
  - 태스크별 타임아웃 설정
- **`systemd/celery-beat.service`** - Celery 스케줄러
  - 주기적 작업 실행

### 4. Nginx 설정
- **`nginx/testcase.run.conf`** - Nginx 리버스 프록시 설정
  - SSL/TLS 설정
  - Rate limiting (API, Auth, Execute)
  - CORS 헤더
  - Gzip 압축
  - 정적 파일 서빙
  - 보안 헤더

### 5. CI/CD
- **`.github/workflows/deploy-ec2.yml`** - GitHub Actions 자동 배포
  - 테스트 실행
  - EC2 SSH 배포
  - 서비스 헬스 체크
  - 실패 시 롤백

### 6. Python 의존성
- **`requirements-production.txt`** - 프로덕션 전용 패키지
  - Django 5.0+
  - Gunicorn (WSGI)
  - Celery + Redis
  - 보안 및 모니터링 패키지

### 7. Django 설정
- **`config/settings_production.py`** - 프로덕션 Django 설정
  - 보안 설정 (HTTPS, HSTS, 쿠키)
  - 데이터베이스 커넥션 풀링
  - Redis 캐싱
  - 로깅 설정
  - WhiteNoise 정적 파일 서빙
  - Sentry 통합 (선택)

### 8. 환경 변수
- **`.env.example`** - 환경 변수 템플릿 (업데이트됨)
  - Django 설정
  - 데이터베이스 설정
  - Redis 설정
  - OAuth 설정
  - AWS 설정
  - 보안 설정
  - 상세한 주석 포함

---

## 배포 단계별 가이드 요약

### Phase 1: AWS 인프라 설정 (30분)
1. **EC2 인스턴스 생성**
   - Ubuntu 22.04 LTS
   - t3.medium (2 vCPU, 4GB RAM)
   - 30GB 스토리지
   - 보안 그룹: 22, 80, 443 포트 오픈

2. **네트워크 설정**
   - Elastic IP 할당
   - DNS A 레코드 설정 (api.testcase.run)

3. **선택사항 (비용 최적화 vs 확장성)**
   - RDS MySQL (추천: 프로덕션)
   - ElastiCache Redis (추천: 고트래픽)
   - S3 버킷 (백업 및 정적 파일)

### Phase 2: 서버 초기 설정 (20분)
```bash
# EC2에 SSH 접속
ssh -i algoitny-ec2-key.pem ubuntu@[ELASTIC_IP]

# setup-ec2.sh 스크립트 실행
sudo bash setup-ec2.sh

# 스크립트가 자동으로 수행:
# - 시스템 업데이트
# - Python 3.11 설치
# - MySQL 설치 및 설정
# - Redis 설치 및 설정
# - Nginx 설치
# - 보안 설정 (UFW, Fail2Ban)
# - 디렉토리 구조 생성
```

### Phase 3: 애플리케이션 배포 (15분)
```bash
# algoitny 유저로 전환
sudo su - algoitny

# 저장소 클론
git clone [YOUR_REPO_URL] /home/algoitny/apps/algoitny

# 초기 배포 실행
cd /home/algoitny/apps/algoitny/backend
bash deploy-scripts/deploy.sh --initial

# .env 파일 편집 (프로덕션 값 입력)
nano .env
```

### Phase 4: 서비스 설정 (10분)
```bash
# Systemd 서비스 파일 복사
sudo cp systemd/gunicorn.service /etc/systemd/system/
sudo cp systemd/celery-worker.service /etc/systemd/system/
sudo cp systemd/celery-beat.service /etc/systemd/system/

# 서비스 시작 및 활성화
sudo systemctl daemon-reload
sudo systemctl enable gunicorn celery-worker celery-beat
sudo systemctl start gunicorn celery-worker celery-beat

# Nginx 설정
sudo cp nginx/testcase.run.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/testcase.run /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Phase 5: SSL 인증서 설정 (5분)
```bash
# Let's Encrypt 인증서 발급
sudo certbot --nginx -d api.testcase.run

# 자동 갱신 테스트
sudo certbot renew --dry-run
```

### Phase 6: 검증 및 테스트 (10분)
```bash
# 서비스 상태 확인
sudo systemctl status gunicorn celery-worker nginx

# Django 배포 체크
source venv/bin/activate
python manage.py check --deploy

# HTTPS 접속 테스트
curl https://api.testcase.run

# API 엔드포인트 테스트
curl https://api.testcase.run/api/problems/
```

### Phase 7: GitHub Actions 설정 (10분)
1. GitHub Repository → Settings → Secrets and variables → Actions
2. 다음 Secrets 추가:
   - `EC2_SSH_PRIVATE_KEY`: EC2 private key 전체 내용
   - `EC2_HOST`: Elastic IP 또는 도메인
   - `EC2_USER`: `algoitny`
   - `AWS_ACCESS_KEY_ID`: AWS access key
   - `AWS_SECRET_ACCESS_KEY`: AWS secret key

3. Push to main → 자동 배포 확인

---

## 필요한 AWS 서비스 및 비용 예상

### 옵션 1: 최소 구성 (EC2 단독) - $30-40/월
**사용 서비스:**
- EC2 t3.medium (24/7)
- Elastic IP (인스턴스 연결 시 무료)
- 데이터 전송 (기본 제공)

**장점:**
- 최저 비용
- 간단한 관리
- 중소규모 트래픽에 적합

**단점:**
- 단일 장애점
- 수동 백업 필요
- 스케일링 어려움

### 옵션 2: 권장 구성 (RDS + ElastiCache) - $70-90/월
**사용 서비스:**
- EC2 t3.medium: ~$35
- RDS db.t3.micro (MySQL): ~$20
- ElastiCache cache.t3.micro (Redis): ~$15
- S3 (백업): ~$2
- 데이터 전송: ~$5
- Route 53: ~$1

**장점:**
- 자동 백업 (RDS)
- 고가용성 옵션
- 관리형 서비스
- 스케일링 용이

**단점:**
- 높은 비용
- 복잡한 설정

### 옵션 3: 엔터프라이즈 구성 (Multi-AZ, Auto Scaling) - $150-200/월
**사용 서비스:**
- Application Load Balancer: ~$20
- EC2 Auto Scaling (2-4 instances): ~$70-140
- RDS Multi-AZ db.t3.small: ~$50
- ElastiCache Redis cluster: ~$30
- CloudWatch: ~$10
- S3 + CloudFront: ~$10

**장점:**
- 고가용성
- 자동 스케일링
- 재해 복구
- 글로벌 CDN

**권장 사항:**
- 개발/테스트: 옵션 1 (EC2 단독)
- 프로덕션 (초기): 옵션 2 (RDS + ElastiCache)
- 프로덕션 (성장 후): 옵션 3 (Multi-AZ)

---

## 보안 체크리스트

### 애플리케이션 보안
- ✅ `DEBUG=False` in production
- ✅ Strong `SECRET_KEY` (auto-generated)
- ✅ `ALLOWED_HOSTS` restricted to domain
- ✅ HTTPS redirect enabled
- ✅ HSTS headers enabled (1 year)
- ✅ Secure cookie settings
- ✅ CSRF protection enabled
- ✅ XSS protection headers
- ✅ Content Security Policy
- ✅ SQL injection protection (Django ORM)
- ✅ Rate limiting (Nginx + DRF)

### 인프라 보안
- ✅ UFW firewall enabled
- ✅ Fail2Ban for brute force protection
- ✅ SSH key-based authentication only
- ✅ No root SSH login
- ✅ Security group: minimal open ports
- ✅ Database: localhost only (or VPC)
- ✅ Redis: localhost only (or VPC)
- ✅ Regular system updates (unattended-upgrades)

### 데이터 보안
- ✅ Database credentials in environment variables
- ✅ API keys in environment variables
- ✅ SSL/TLS for all traffic
- ✅ Encrypted database backups
- ✅ S3 bucket private by default
- ✅ No sensitive data in logs

### 액세스 제어
- ✅ IAM users with minimal permissions
- ✅ Django admin URL can be customized
- ✅ Strong password policies
- ✅ JWT token expiration
- ✅ Session timeout

---

## 문제 해결 팁

### 1. Gunicorn이 시작하지 않는 경우
```bash
# 로그 확인
sudo journalctl -u gunicorn -n 50

# 일반적인 원인:
# - 소켓 파일 권한 문제
sudo chown algoitny:www-data /home/algoitny/apps/algoitny/backend/gunicorn.sock

# - Python 경로 문제
/home/algoitny/apps/algoitny/backend/venv/bin/python --version

# - 환경 변수 문제
cat /home/algoitny/apps/algoitny/backend/.env

# 수동 실행 테스트
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
gunicorn config.wsgi:application
```

### 2. Nginx 502 Bad Gateway
```bash
# Gunicorn 상태 확인
sudo systemctl status gunicorn

# 소켓 파일 확인
ls -la /home/algoitny/apps/algoitny/backend/gunicorn.sock

# Nginx 에러 로그
sudo tail -f /var/log/nginx/algoitny_error.log

# 권한 확인
sudo usermod -aG www-data nginx
```

### 3. 정적 파일이 로드되지 않음
```bash
# 정적 파일 수집
python manage.py collectstatic --noinput

# 권한 확인
sudo chown -R algoitny:www-data staticfiles/
sudo chmod -R 755 staticfiles/

# Nginx 설정 확인
sudo nginx -t
```

### 4. Celery 태스크가 실행되지 않음
```bash
# Redis 상태 확인
redis-cli ping

# Celery 워커 상태
sudo systemctl status celery-worker

# Celery 로그
sudo journalctl -u celery-worker -f

# 수동 테스트
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate
celery -A config worker --loglevel=debug
```

### 5. 데이터베이스 연결 오류
```bash
# MySQL 상태 확인
sudo systemctl status mysql

# 데이터베이스 접속 테스트
mysql -u algoitny -p

# 연결 설정 확인
python manage.py dbshell

# .env 파일 확인
cat .env | grep DB_
```

### 6. SSL 인증서 문제
```bash
# 인증서 상태 확인
sudo certbot certificates

# 수동 갱신
sudo certbot renew

# Nginx 설정 테스트
sudo nginx -t

# SSL Labs 테스트
# https://www.ssllabs.com/ssltest/
```

### 7. 높은 메모리 사용
```bash
# 메모리 확인
free -h
htop

# Gunicorn worker 줄이기 (임시)
# Edit /etc/systemd/system/gunicorn.service
# --workers 2 (instead of 4)

# 서비스 재시작
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### 8. 디스크 공간 부족
```bash
# 디스크 사용량 확인
df -h

# 큰 파일 찾기
sudo du -sh /* | sort -rh | head -10

# 로그 파일 정리
sudo journalctl --vacuum-time=7d
sudo find /var/log -name "*.log.*" -mtime +7 -delete

# Python 캐시 정리
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
```

---

## 다음 단계

### 즉시 수행
1. ✅ 모든 환경 변수 설정
2. ✅ 첫 배포 실행
3. ✅ SSL 인증서 설정
4. ✅ 헬스 체크 엔드포인트 테스트
5. ✅ 모니터링 설정

### 1주일 내
1. 백업 자동화 설정 및 테스트
2. 재해 복구 계획 수립
3. 모니터링 알림 설정
4. 로드 테스트 실행
5. 문서화 완료

### 1개월 내
1. 성능 최적화 (쿼리, 캐싱)
2. 비용 최적화 검토
3. 보안 감사
4. 스케일링 전략 수립
5. 팀 교육

---

## 참고 자료

### 공식 문서
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Deployment](https://docs.gunicorn.org/en/stable/deploy.html)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Celery Production](https://docs.celeryproject.org/en/stable/userguide/deployment.html)
- [AWS EC2 User Guide](https://docs.aws.amazon.com/ec2/)

### 보안 테스트 도구
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Security Headers](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)

### 모니터링 도구
- [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)
- [Sentry](https://sentry.io/) - Error tracking
- [New Relic](https://newrelic.com/) - APM
- [Datadog](https://www.datadoghq.com/) - Infrastructure

---

## 지원 및 문의

배포 과정에서 문제가 발생하면:

1. **로그 확인**: 대부분의 문제는 로그에서 확인 가능
2. **체크리스트 확인**: `DEPLOYMENT_CHECKLIST.md` 참조
3. **문제 해결 가이드**: 위의 "문제 해결 팁" 섹션 참조
4. **AWS 문서**: 서비스별 공식 문서 확인
5. **Django 문서**: Django 관련 문제는 공식 문서 참조

**중요**: 프로덕션 환경에서 실험하지 마세요. 항상 스테이징 환경에서 먼저 테스트하세요.

---

**배포 완료를 축하합니다!** 🚀

이제 api.testcase.run에서 AlgoItny 백엔드가 실행되고 있습니다.
