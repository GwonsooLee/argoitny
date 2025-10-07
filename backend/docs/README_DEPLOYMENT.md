# AlgoItny Backend - AWS EC2 Deployment Guide

Django 백엔드를 AWS EC2에 프로덕션 배포하기 위한 완전한 가이드입니다.

## 빠른 시작 (Quick Start)

### 전제 조건
- AWS 계정
- 도메인 (api.testcase.run)
- GitHub 저장소
- SSH 클라이언트

### 배포 단계 (총 소요 시간: ~90분)

#### 1. EC2 인스턴스 생성 (10분)
```bash
# AWS Console에서:
# - Ubuntu 22.04 LTS
# - t3.medium
# - 30GB 스토리지
# - 보안 그룹: 22, 80, 443
# - Elastic IP 할당
```

#### 2. 서버 초기 설정 (20분)
```bash
# SSH 접속
ssh -i your-key.pem ubuntu@[ELASTIC_IP]

# 스크립트 다운로드 및 실행
wget https://raw.githubusercontent.com/[YOUR_REPO]/main/backend/deploy-scripts/setup-ec2.sh
sudo bash setup-ec2.sh
```

#### 3. 애플리케이션 배포 (30분)
```bash
# algoitny 유저로 전환
sudo su - algoitny

# 저장소 클론
git clone [YOUR_REPO_URL] /home/algoitny/apps/algoitny
cd /home/algoitny/apps/algoitny/backend

# 초기 배포
bash deploy-scripts/deploy.sh --initial

# .env 파일 설정
cp .env.example .env
nano .env  # 프로덕션 값 입력
```

#### 4. 서비스 설정 (20분)
```bash
# Systemd 서비스 설치
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn celery-worker celery-beat

# Nginx 설정
sudo cp nginx/testcase.run.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/testcase.run /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

#### 5. SSL 인증서 (5분)
```bash
sudo certbot --nginx -d api.testcase.run
```

#### 6. 검증 (5분)
```bash
# 서비스 확인
sudo systemctl status gunicorn celery-worker nginx

# HTTPS 테스트
curl https://api.testcase.run/api/problems/
```

---

## 문서 구조

### 📚 주요 문서
1. **[AWS_EC2_DEPLOYMENT.md](./AWS_EC2_DEPLOYMENT.md)** ⭐ 메인 가이드
   - 완전한 단계별 배포 가이드
   - AWS 서비스 설정
   - 보안 설정
   - 모니터링 및 백업
   - 문제 해결

2. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** ✅ 체크리스트
   - 배포 전 체크리스트
   - 배포 후 검증
   - 유지보수 작업
   - 긴급 상황 대응

3. **[DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)** 📊 요약
   - 생성된 파일 목록
   - 배포 단계 요약
   - 비용 예상
   - 보안 체크리스트
   - 문제 해결 팁

### 🛠 배포 스크립트
- **deploy-scripts/setup-ec2.sh** - EC2 초기 설정 자동화
- **deploy-scripts/deploy.sh** - 애플리케이션 배포/업데이트

### ⚙️ 설정 파일
- **systemd/** - Systemd 서비스 파일
  - gunicorn.service
  - celery-worker.service
  - celery-beat.service
- **nginx/** - Nginx 설정
  - testcase.run.conf
- **.github/workflows/** - GitHub Actions CI/CD
  - deploy-ec2.yml

### 📦 Python 패키지
- **requirements-production.txt** - 프로덕션 의존성
- **config/settings_production.py** - 프로덕션 Django 설정

### 🔐 환경 변수
- **.env.example** - 환경 변수 템플릿 (업데이트됨)

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                    HTTPS (443)
                         │
                         ▼
            ┌────────────────────────┐
            │   Route 53 (DNS)       │
            │  api.testcase.run      │
            └────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │   EC2 Instance         │
            │   (Ubuntu 22.04)       │
            │                        │
            │  ┌──────────────────┐  │
            │  │  Nginx           │  │ ← Reverse Proxy, SSL
            │  │  (Port 80/443)   │  │
            │  └────────┬─────────┘  │
            │           │             │
            │           ▼             │
            │  ┌──────────────────┐  │
            │  │  Gunicorn        │  │ ← WSGI Server
            │  │  (4 workers)     │  │
            │  └────────┬─────────┘  │
            │           │             │
            │           ▼             │
            │  ┌──────────────────┐  │
            │  │  Django App      │  │ ← Application
            │  │  (Python 3.11)   │  │
            │  └──┬───────────┬───┘  │
            │     │           │       │
            │     ▼           ▼       │
            │  ┌─────┐    ┌───────┐  │
            │  │MySQL│    │ Redis │  │ ← Database & Cache
            │  └─────┘    └───┬───┘  │
            │                 │       │
            │                 ▼       │
            │  ┌──────────────────┐  │
            │  │  Celery Worker   │  │ ← Async Tasks
            │  └──────────────────┘  │
            └────────────────────────┘
```

---

## 주요 특징

### 🚀 성능 최적화
- ✅ Gunicorn WSGI 서버 (4 workers)
- ✅ Nginx 리버스 프록시 및 정적 파일 서빙
- ✅ Redis 캐싱
- ✅ 데이터베이스 커넥션 풀링
- ✅ Gzip 압축
- ✅ HTTP/2 지원

### 🔒 보안
- ✅ HTTPS/SSL (Let's Encrypt)
- ✅ HSTS 헤더 (1년)
- ✅ 보안 쿠키 설정
- ✅ CSRF 보호
- ✅ Rate Limiting
- ✅ UFW 방화벽
- ✅ Fail2Ban
- ✅ SSH 키 인증만 허용

### 📊 모니터링
- ✅ Systemd 서비스 관리
- ✅ 로그 로테이션
- ✅ CloudWatch 통합 (선택)
- ✅ Sentry 에러 추적 (선택)

### 🔄 CI/CD
- ✅ GitHub Actions 자동 배포
- ✅ 자동 테스트
- ✅ 실패 시 롤백
- ✅ 배포 알림

---

## 비용 예상

### 최소 구성 (EC2 단독)
- **월 비용**: $30-40
- **사용**: 개발/테스트, 소규모 트래픽
- **서비스**: EC2 t3.medium, Elastic IP

### 권장 구성 (RDS + ElastiCache)
- **월 비용**: $70-90
- **사용**: 프로덕션 (초기)
- **서비스**: EC2, RDS MySQL, ElastiCache Redis, S3

### 엔터프라이즈 구성
- **월 비용**: $150-200
- **사용**: 프로덕션 (고트래픽)
- **서비스**: Auto Scaling, Multi-AZ RDS, ALB, CloudFront

---

## 환경 변수 설정

**.env 파일 필수 항목:**
```bash
# Django
SECRET_KEY=<generate-new-key>
DEBUG=False
ALLOWED_HOSTS=api.testcase.run

# Database
DB_NAME=algoitny
DB_USER=algoitny
DB_PASSWORD=<strong-password>
DB_HOST=localhost

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>

# API Keys
GEMINI_API_KEY=<your-api-key>

# CORS
CORS_ALLOWED_ORIGINS=https://testcase.run

# Security
SECURE_SSL_REDIRECT=True
```

전체 환경 변수 목록은 `.env.example` 참조

---

## GitHub Actions 설정

**GitHub Secrets 추가:**
1. Repository → Settings → Secrets and variables → Actions
2. 다음 Secrets 추가:
   - `EC2_SSH_PRIVATE_KEY`: EC2 private key 전체 내용
   - `EC2_HOST`: Elastic IP 또는 도메인
   - `EC2_USER`: `algoitny`
   - `AWS_ACCESS_KEY_ID`: AWS access key
   - `AWS_SECRET_ACCESS_KEY`: AWS secret key

**자동 배포:**
- `main` 브랜치에 push하면 자동 배포
- 테스트 실패 시 배포 중단
- 배포 실패 시 자동 롤백

---

## 유용한 명령어

### 서비스 관리
```bash
# 상태 확인
sudo systemctl status gunicorn celery-worker nginx

# 재시작
sudo systemctl restart gunicorn celery-worker

# 로그 확인
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/nginx/algoitny_error.log
```

### Django 관리
```bash
cd /home/algoitny/apps/algoitny/backend
source venv/bin/activate

# 마이그레이션
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic

# 배포 체크
python manage.py check --deploy
```

### 배포
```bash
# 수동 배포
cd /home/algoitny/apps/algoitny/backend
bash deploy-scripts/deploy.sh

# GitHub Actions로 자동 배포
git push origin main
```

### 백업
```bash
# 데이터베이스 백업
mysqldump -u algoitny -p algoitny > backup.sql

# 백업 복원
mysql -u algoitny -p algoitny < backup.sql
```

---

## 문제 해결

### Gunicorn 시작 실패
```bash
# 로그 확인
sudo journalctl -u gunicorn -n 50

# 권한 확인
sudo chown -R algoitny:www-data /home/algoitny/apps/algoitny/backend

# 수동 실행 테스트
source venv/bin/activate
gunicorn config.wsgi:application
```

### Nginx 502 Error
```bash
# Gunicorn 상태 확인
sudo systemctl status gunicorn

# 소켓 파일 확인
ls -la /home/algoitny/apps/algoitny/backend/gunicorn.sock

# Nginx 재시작
sudo systemctl restart nginx
```

### 정적 파일 404
```bash
# 정적 파일 재수집
python manage.py collectstatic --noinput

# 권한 설정
sudo chmod -R 755 staticfiles/
```

더 많은 문제 해결 팁은 [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md) 참조

---

## 보안 체크리스트

배포 전 확인:
- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` 설정
- [ ] HTTPS 활성화
- [ ] 방화벽 활성화
- [ ] SSH 키 인증만 허용
- [ ] 데이터베이스 강력한 비밀번호
- [ ] 정기 백업 설정

자세한 보안 체크리스트는 [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) 참조

---

## 유지보수

### 일일
- 에러 로그 확인
- 디스크 공간 확인
- 백업 완료 확인

### 주간
- 시스템 리소스 모니터링
- 보안 로그 검토
- 백업 복원 테스트

### 월간
- 시스템 업데이트
- SSL 인증서 확인
- 성능 최적화 검토
- Django/패키지 업데이트

---

## 추가 리소스

### 문서
- [Django 배포 가이드](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Gunicorn 문서](https://docs.gunicorn.org/)
- [Nginx 문서](https://nginx.org/en/docs/)
- [Celery 배포](https://docs.celeryproject.org/en/stable/userguide/deployment.html)

### 도구
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)
- [Security Headers](https://securityheaders.com/)
- [GTmetrix](https://gtmetrix.com/)

### 모니터링 서비스
- [Sentry](https://sentry.io/) - 에러 추적
- [New Relic](https://newrelic.com/) - APM
- [Datadog](https://www.datadoghq.com/) - 인프라 모니터링

---

## 지원

문제가 발생하면:
1. 로그 확인
2. [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)의 문제 해결 섹션 참조
3. [AWS 공식 문서](https://docs.aws.amazon.com/) 확인
4. 팀에 문의

---

## 라이선스

이 배포 가이드는 AlgoItny 프로젝트의 일부입니다.

---

**배포를 축하합니다!** 🎉

문의사항이나 개선 제안이 있으면 이슈를 생성해주세요.
