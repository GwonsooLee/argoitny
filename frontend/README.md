# Algoitny Frontend

React + Vite 기반 프론트엔드 애플리케이션

## 기술 스택

- **React 19**: UI 라이브러리
- **Vite**: 빌드 도구
- **Material-UI (MUI)**: UI 컴포넌트 라이브러리
- **Emotion**: CSS-in-JS 스타일링

## 개발 환경 설정

### 사전 요구사항

- Node.js 18 이상
- npm 9 이상

### 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 시작
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 결과 미리보기
npm run preview
```

### 환경 변수 설정

환경별 설정 파일:
- `.env.development`: 개발 환경
- `.env.production`: 프로덕션 환경

필수 환경 변수:
```env
VITE_API_URL=https://api.testcase.run/api
VITE_ENV=production
```

## 배포

### AWS CloudFront 배포 (권장)

전 세계 사용자에게 빠르게 콘텐츠를 제공하기 위해 AWS CloudFront를 사용합니다.

#### 빠른 시작
```bash
# 배포 스크립트 실행
./deploy-scripts/deploy-to-s3.sh algoitny-frontend-prod E1XXXXXXXXXX
```

#### 자동 배포 (GitHub Actions)
`main` 브랜치에 push하면 자동으로 배포됩니다.

필요한 GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `CLOUDFRONT_DISTRIBUTION_ID`

#### 상세 가이드
- [빠른 시작 가이드](./QUICKSTART_DEPLOYMENT.md)
- [상세 배포 가이드](./AWS_CLOUDFRONT_DEPLOYMENT.md)
- [배포 체크리스트](./DEPLOYMENT_CHECKLIST.md)
- [GitHub Secrets 설정](./GITHUB_SECRETS_SETUP.md)

### Vercel 배포 (대안)

Vercel을 사용한 간편한 배포도 지원합니다.

- [Vercel 배포 가이드](./VERCEL_DEPLOYMENT.md)

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/        # React 컴포넌트
│   ├── config/           # 설정 파일 (API 엔드포인트 등)
│   ├── utils/            # 유틸리티 함수
│   ├── App.jsx           # 메인 앱 컴포넌트
│   └── main.jsx          # 엔트리 포인트
├── public/               # 정적 파일
├── .github/
│   └── workflows/        # GitHub Actions 워크플로우
├── deploy-scripts/       # 배포 스크립트
└── dist/                 # 빌드 결과물 (생성됨)
```

## 주요 기능

- Google OAuth 로그인
- 알고리즘 문제 검색 및 관리
- 코드 실행 및 테스트
- 문제 등록 및 관리
- 검색 히스토리

## 개발 가이드

### 코드 스타일

```bash
# ESLint 실행
npm run lint
```

### 빌드 최적화

- Vite의 코드 스플리팅 활용
- 동적 import로 청크 분할
- 이미지 최적화 (WebP, lazy loading)

## 문제 해결

### 일반적인 이슈

**빌드 실패**
```bash
# node_modules 삭제 후 재설치
rm -rf node_modules package-lock.json
npm install
```

**API 연결 실패**
- `.env.development` 또는 `.env.production` 파일의 `VITE_API_URL` 확인
- 백엔드 서버가 실행 중인지 확인

**CORS 에러**
- 백엔드에서 CORS 설정 확인
- `django-cors-headers` 설정 확인

## 라이선스

MIT License

## 기여

이슈나 PR은 언제든지 환영합니다!
