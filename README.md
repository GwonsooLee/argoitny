# AlgoItny

알고리즘 반례 검증 플랫폼 - Codeforces, Baekjoon 문제의 반례를 수집하고 코드를 테스트할 수 있습니다.

## 🚀 주요 기능

- 📝 문제 검색 (Codeforces, Baekjoon)
- 💻 다중 언어 코드 실행 (Python, JavaScript, C++, Java)
- ✅ 자동 테스트 케이스 검증
- 🤖 AI 기반 테스트 케이스 생성 (Gemini API)
- 🔐 Google OAuth 로그인
- 📊 검색 기록 관리
- 🔄 실시간 코드 실행 결과

## 🛠️ 기술 스택

### Backend
- Django 5.2
- Django REST Framework
- MySQL 8.0
- Google Gemini AI
- JWT Authentication

### Frontend
- React 18
- Vite
- Google OAuth

### Infrastructure
- Docker & Docker Compose
- Nginx

## 📋 사전 요구사항

- Docker & Docker Compose
- Git
- Google OAuth Client ID (선택사항)
- Google Gemini API Key (선택사항)

## 🏁 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd algoitny
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# Database
DB_NAME=algoitny
DB_USER=root
DB_PASSWORD=rootpassword

# Django
SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,backend

# Google OAuth (선택사항)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Gemini API (선택사항)
GEMINI_API_KEY=your-gemini-api-key

# Code Execution
CODE_EXECUTION_TIMEOUT=5
```

### 3. 서비스 시작

```bash
make up
```

### 4. 접속

- 프론트엔드: http://localhost:5173
- 백엔드 API: http://localhost:8000
- MySQL: localhost:3306

## 📖 Makefile 명령어

### 기본 명령어

```bash
make help          # 모든 명령어 보기
make up            # 서비스 시작
make down          # 서비스 중지
make restart       # 서비스 재시작
make ps            # 상태 확인
make logs          # 전체 로그 보기
```

### 개별 서비스

```bash
make restart-backend   # 백엔드만 재시작
make restart-frontend  # 프론트엔드만 재시작
make logs-backend      # 백엔드 로그
make logs-frontend     # 프론트엔드 로그
```

### 빌드

```bash
make build         # 이미지 다시 빌드
make rebuild       # 완전히 새로 빌드
```

### 개발 도구

```bash
make shell-backend     # 백엔드 쉘 접속
make shell-frontend    # 프론트엔드 쉘 접속
make shell-mysql       # MySQL 접속
make migrate           # Django 마이그레이션
make createsuperuser   # 관리자 계정 생성
```

### 정리

```bash
make clean             # 모든 것 제거
make clean-volumes     # 볼륨만 제거
make fresh             # 완전 초기화
```

## 🔐 Google OAuth 설정

### 1. Google Cloud Console 설정

1. https://console.cloud.google.com/ 접속
2. 프로젝트 생성 또는 선택
3. APIs & Services > OAuth consent screen 설정
4. APIs & Services > Credentials > OAuth client ID 생성

### 2. Authorized JavaScript origins

```
http://localhost:5173
http://localhost:8000
```

### 3. Authorized redirect URIs

```
http://localhost:5173
http://localhost:5173/
```

### 4. Client ID 및 Secret 복사

`.env` 파일에 추가:

```env
GOOGLE_CLIENT_ID=your-actual-client-id
GOOGLE_CLIENT_SECRET=your-actual-client-secret
```

### 5. 서비스 재시작

```bash
make restart
```

## 🤖 Gemini API 설정 (문제 등록용)

1. https://makersuite.google.com/app/apikey 접속
2. API 키 생성
3. `.env` 파일에 추가:

```env
GEMINI_API_KEY=your-gemini-api-key
```

4. 서비스 재시작:

```bash
make restart
```

## 📁 프로젝트 구조

```
algoitny/
├── backend/              # Django 백엔드
│   ├── config/          # Django 설정
│   ├── api/             # API 앱
│   │   ├── models.py    # 데이터베이스 모델
│   │   ├── views/       # API 뷰
│   │   ├── serializers.py
│   │   └── services/    # 비즈니스 로직
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/            # React 프론트엔드
│   ├── src/
│   │   ├── components/  # React 컴포넌트
│   │   ├── config/      # API 설정
│   │   └── utils/       # 유틸리티
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── Makefile
├── .env                 # 환경 변수 (git에 포함 안 됨)
├── .gitignore
└── README.md
```

## 🐛 문제 해결

### 포트가 이미 사용 중인 경우

```bash
# 실행 중인 컨테이너 확인
docker ps

# 특정 포트 사용 확인
lsof -i :5173
lsof -i :8000
lsof -i :3306

# 모든 서비스 중지
make down
```

### 데이터베이스 연결 오류

```bash
# MySQL 로그 확인
make logs-mysql

# 데이터베이스 재시작
docker-compose restart mysql
```

### 환경 변수가 적용되지 않는 경우

```bash
# 서비스 재시작
make restart

# 완전히 다시 빌드
make rebuild
```

## 📝 API 엔드포인트

### 인증
- `POST /api/auth/google/` - Google OAuth 로그인
- `POST /api/auth/refresh/` - JWT 토큰 리프레시
- `POST /api/auth/logout/` - 로그아웃

### 문제
- `GET /api/problems/` - 문제 목록 (검색 가능)
- `GET /api/problems/{id}/` - 문제 상세

### 코드 실행
- `POST /api/execute/` - 코드 실행 및 테스트

### 검색 기록
- `GET /api/history/` - 검색 기록 (페이지네이션)
- `GET /api/history/{id}/` - 검색 기록 상세

### 문제 등록
- `POST /api/register/problem/` - 문제 등록
- `POST /api/register/generate-test-cases/` - AI 테스트 케이스 생성

## 🚢 배포

### 프로덕션 환경 변수

```env
SECRET_KEY=<강력한-비밀키-생성>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

### HTTPS 설정

프로덕션 환경에서는 반드시 HTTPS를 사용하세요.

## 📄 라이센스

MIT License

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 문의

프로젝트 관련 문의사항은 Issue를 등록해주세요.
