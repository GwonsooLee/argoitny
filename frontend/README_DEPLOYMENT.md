# Vercel 배포 빠른 시작 가이드

이 문서는 Vercel 배포의 핵심 내용을 요약합니다. 상세한 내용은 [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)를 참고하세요.

## 빠른 시작

### 1. 환경 변수 설정

Vercel 대시보드 > Settings > Environment Variables에서 다음을 추가:

```
VITE_API_URL=https://api.testcase.run/api
VITE_ENV=production
```

### 2. 빌드 설정

Vercel은 자동으로 다음 설정을 감지합니다:

- Framework: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- Root Directory: `frontend`

### 3. 배포

```bash
# main 브랜치에 푸시하면 자동 배포
git push origin main
```

## 환경별 API 엔드포인트

| 환경 | API URL | 파일 |
|-----|---------|------|
| Development | `http://localhost:8000/api` | `.env.development` |
| Production | `https://api.testcase.run/api` | `.env.production` |

## 로컬 테스트

```bash
# 개발 모드 (localhost API)
npm run dev

# 프로덕션 빌드 테스트
npm run build
npm run preview
```

## 주요 파일

- `.env.development` - 개발 환경 변수
- `.env.production` - 프로덕션 환경 변수
- `.env.example` - 환경 변수 템플릿
- `vercel.json` - Vercel 설정 (SPA 라우팅)
- `src/config/api.js` - API 설정

## 문제 해결

### 빌드 실패
1. 로컬에서 `npm run build` 테스트
2. Vercel 배포 로그 확인
3. 환경 변수 확인

### API 연결 실패
1. 브라우저 콘솔에서 API URL 확인
2. 백엔드 CORS 설정 확인
3. Vercel 환경 변수 재확인

### 404 에러 (새로고침 시)
- `vercel.json` 파일 확인 (이미 설정됨)

## Vercel CLI

```bash
# 설치
npm install -g vercel

# 배포
vercel --prod

# 환경 변수 관리
vercel env ls
```

## 더 알아보기

상세한 배포 가이드는 [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)를 참고하세요.
