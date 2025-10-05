# AlgoItny - 알고리즘 반례 검증 플랫폼

Codeforces와 백준의 문제 반례를 모아서 사용자 코드를 검증하는 애플리케이션입니다.

## 주요 기능

### 반례 검증
- **플랫폼 선택**: 백준(Baekjoon)과 Codeforces 지원
- **문제 검색**: 문제 번호 또는 제목으로 검색
- **코드 입력 및 언어 자동 감지**: Python, JavaScript, C++, Java 지원
- **반례 자동 검증**: 저장된 반례로 코드 실행 및 결과 비교
- **결과 표시**: 통과한 테스트와 실패한 반례를 명확하게 표시

### 문제 등록 (NEW!)
- **AI 기반 반례 생성**: Gemini API를 활용하여 자동으로 100개 이상의 반례 생성
- **정답 코드 실행**: 생성된 반례로 정답 코드를 실행하여 정답 출력 자동 생성
- **데이터베이스 저장**: 문제와 반례를 데이터베이스에 저장하여 재사용

## 기술 스택

### 백엔드
- Node.js + Express
- MySQL 8.0
- Google Gemini API (반례 생성)
- Child Process (코드 실행)

### 프론트엔드
- React (Vite)
- Nginx

### 인프라
- Docker & Docker Compose
- MySQL 8.0

## 빠른 시작 (Docker 사용)

### 1. 환경 변수 설정

루트 디렉토리에 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 내용:
```bash
# Database Configuration
DB_HOST=mysql
DB_USER=root
DB_PASSWORD=rootpassword
DB_NAME=algoitny

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
```

**Gemini API 키 발급 방법:**
1. [Google AI Studio](https://makersuite.google.com/app/apikey)에 접속
2. "Get API Key" 클릭
3. API 키를 `.env` 파일에 입력

### 2. Docker Compose로 실행

```bash
# 전체 애플리케이션 실행 (MySQL + 백엔드 + 프론트엔드)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down

# 데이터베이스 포함 완전 삭제
docker-compose down -v
```

### 3. 샘플 데이터 추가

```bash
# 컨테이너가 실행 중일 때
docker-compose exec backend node seed.js
```

### 4. 애플리케이션 접속

브라우저에서 `http://localhost` 접속

---

## 로컬 개발 환경 (Docker 없이)

### 사전 요구사항
- Node.js 18+
- MySQL 8.0
- Python 3
- g++ (C++ 지원)
- Java JDK (Java 지원)

### 1. MySQL 설치 및 실행

```bash
# MySQL 데이터베이스 생성
mysql -u root -p
CREATE DATABASE algoitny;
```

### 2. 의존성 설치

```bash
# 루트, 백엔드, 프론트엔드 모든 의존성 설치
npm run install-all
```

### 3. 환경 변수 설정

```bash
cd backend
cp .env.example .env
```

`.env` 파일 수정:
```bash
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=algoitny
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. 데이터베이스 초기화

```bash
cd backend
node seed.js
```

### 5. 개발 서버 실행

```bash
# 루트 디렉토리에서 백엔드 + 프론트엔드 동시 실행
npm run dev
```

### 6. 애플리케이션 접속

브라우저에서 `http://localhost:5173` 접속

## 사용 방법

### 반례 검증 사용법
1. **플랫폼 선택**: 백준 또는 Codeforces 선택
2. **문제 검색**: 문제 번호(예: 1000) 또는 제목(예: A+B) 입력
3. **문제 선택**: 검색 결과에서 원하는 문제 클릭
4. **코드 입력**: 텍스트 영역에 코드 입력
5. **언어 확인/변경**: 자동 감지된 언어 확인 및 필요시 변경
6. **검증 실행**: "반례 검증하기" 버튼 클릭
7. **결과 확인**: 통과/실패 반례 확인

### 문제 등록 사용법
1. **문제 등록 페이지 이동**: 메인 페이지에서 "+ 문제 등록" 버튼 클릭
2. **문제 정보 입력**:
   - 플랫폼 선택 (백준 또는 Codeforces)
   - 문제 번호 입력 (예: 1000)
   - 문제 제목 입력 (예: A+B)
3. **정답 코드 입력**: 정답 코드 작성 (언어 자동 감지)
4. **입력 조건 입력**: 문제의 입력 변수 조건 상세히 기술
5. **반례 생성**: "반례 생성 (100개)" 버튼 클릭하여 AI가 반례 생성
6. **문제 등록**: 생성된 반례 확인 후 "문제 등록" 버튼 클릭
7. **완료**: 정답 코드로 모든 반례 실행 후 DB에 저장

## 샘플 문제

데이터베이스에는 다음 샘플 문제들이 포함되어 있습니다:

### 백준
- 1000: A+B
- 2557: Hello World
- 10869: 사칙연산

### Codeforces
- 1A: Theatre Square
- 4A: Watermelon

## 프로젝트 구조

```
algoitny/
├── docker-compose.yml     # Docker Compose 설정
├── .env                   # 환경 변수
├── .env.example          # 환경 변수 예시
├── backend/
│   ├── Dockerfile        # 백엔드 Docker 이미지
│   ├── server.js         # Express 서버 (MySQL)
│   ├── db.js             # MySQL 연결 풀
│   ├── geminiService.js  # Gemini API 서비스
│   ├── seed.js           # 샘플 데이터
│   ├── .env              # 환경 변수
│   ├── package.json
│   └── temp/             # 코드 실행 임시 파일
├── frontend/
│   ├── Dockerfile        # 프론트엔드 Docker 이미지
│   ├── nginx.conf        # Nginx 설정
│   ├── src/
│   │   ├── App.jsx       # 메인 앱 컴포넌트
│   │   ├── components/
│   │   │   ├── ProblemSearch.jsx   # 문제 검색
│   │   │   ├── ProblemRegister.jsx # 문제 등록
│   │   │   ├── CodeEditor.jsx      # 코드 입력
│   │   │   └── TestResults.jsx     # 결과 표시
│   │   └── ...
│   └── package.json
└── mysql-init/           # MySQL 초기화 스크립트
```

## Docker 구성

### 컨테이너 구성
- **MySQL**: 포트 3306, 데이터 영구 저장
- **Backend**: 포트 5000, Node.js + Express
- **Frontend**: 포트 80, React + Nginx

### 네트워크
모든 컨테이너는 `algoitny-network` 브리지 네트워크로 연결됩니다.

### 볼륨
- `mysql_data`: MySQL 데이터 영구 저장

## API 엔드포인트

### GET /api/problems/search
문제 검색

**Parameters:**
- `platform`: 'baekjoon' | 'codeforces'
- `query`: 검색어 (문제 번호 또는 제목)

### GET /api/problems/:id/testcases
문제의 테스트 케이스 조회

### POST /api/execute
코드 실행 및 검증

**Body:**
```json
{
  "code": "소스 코드",
  "language": "python | javascript | cpp | java",
  "problemId": 1
}
```

### POST /api/generate-testcases
Gemini API를 사용하여 반례 생성

**Body:**
```json
{
  "platform": "baekjoon | codeforces",
  "problemId": "1000",
  "title": "A+B",
  "solutionCode": "정답 코드",
  "language": "python | javascript | cpp | java",
  "constraints": "입력 변수 조건 설명"
}
```

### POST /api/problems/register
새 문제 등록

**Body:**
```json
{
  "platform": "baekjoon | codeforces",
  "problemId": "1000",
  "title": "A+B",
  "solutionCode": "정답 코드",
  "language": "python | javascript | cpp | java",
  "testCases": [{"input": "1 2"}, {"input": "3 4"}, ...]
}
```

## 지원 언어

- **Python**: Python 3
- **JavaScript**: Node.js
- **C++**: g++ 컴파일러 필요
- **Java**: JDK 필요

## 주의사항

- **Gemini API 키 필수**: 문제 등록 기능을 사용하려면 Gemini API 키가 필요합니다
- **Docker 필수**: Docker와 Docker Compose가 설치되어 있어야 합니다
- **포트**: 80번 포트(프론트엔드), 5000번 포트(백엔드), 3306번 포트(MySQL)가 사용 가능해야 합니다
- **컴파일러**: Docker 이미지에 Python3, g++, OpenJDK11이 포함되어 있습니다
- **타임아웃**: 코드 실행 타임아웃은 5초로 설정되어 있습니다
- **보안**: 프로덕션 환경에서는 코드 실행을 샌드박스 환경에서 수행하는 것을 권장합니다
- **API 사용량**: Gemini API는 무료 할당량이 있으니 사용량에 주의하세요
- **데이터 영속성**: `docker-compose down -v`를 실행하면 모든 데이터베이스 데이터가 삭제됩니다

## 반례 생성 프롬프트

Gemini API는 다음과 같은 기준으로 반례를 생성합니다:
- **Edge Cases (20개)**: 최소값, 최대값, 경계 조건
- **Small Cases (30개)**: 수동 검증 가능한 간단한 입력
- **Medium Cases (30개)**: 중간 복잡도 입력
- **Large Cases (20개)**: 최대 범위에 가까운 대규모 입력

총 100개의 다양한 반례가 자동으로 생성됩니다.

## Docker 명령어

```bash
# 전체 빌드 및 실행
docker-compose up --build -d

# 특정 서비스만 재시작
docker-compose restart backend

# 로그 확인
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mysql

# 컨테이너 상태 확인
docker-compose ps

# 데이터베이스 접속
docker-compose exec mysql mysql -u root -p

# 백엔드 컨테이너 접속
docker-compose exec backend sh

# 샘플 데이터 삽입
docker-compose exec backend node seed.js
```

## 향후 개선 사항

- LeetCode, Programmers 플랫폼 지원
- 사용자 계정 및 히스토리 기능
- 코드 에디터 개선 (Syntax Highlighting)
- 반례 생성 개수 커스터마이징
- 생성된 반례 수동 편집 기능
- Kubernetes 배포 지원

## 라이선스

ISC
