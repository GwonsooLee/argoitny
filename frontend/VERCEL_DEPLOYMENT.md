# Vercel 배포 가이드

이 문서는 Algoitny 프론트엔드를 Vercel에 배포하는 방법을 단계별로 설명합니다.

## 목차
1. [사전 준비](#사전-준비)
2. [Vercel 계정 생성 및 프로젝트 설정](#vercel-계정-생성-및-프로젝트-설정)
3. [GitHub 저장소 연동](#github-저장소-연동)
4. [환경 변수 설정](#환경-변수-설정)
5. [빌드 설정](#빌드-설정)
6. [배포 프로세스](#배포-프로세스)
7. [도메인 설정](#도메인-설정)
8. [프로덕션 vs 프리뷰 배포](#프로덕션-vs-프리뷰-배포)
9. [문제 해결 (Troubleshooting)](#문제-해결-troubleshooting)

---

## 사전 준비

배포하기 전에 다음 사항을 확인하세요:

- [ ] GitHub 계정이 있고, 프로젝트가 GitHub에 푸시되어 있음
- [ ] Node.js 18.x 이상 설치됨
- [ ] 프로젝트가 로컬에서 정상적으로 빌드됨 (`npm run build`)
- [ ] 백엔드 API가 배포되어 있고 접근 가능함 (https://api.testcase.run)

## Vercel 계정 생성 및 프로젝트 설정

### 1. Vercel 계정 생성

1. [Vercel 웹사이트](https://vercel.com)에 접속
2. "Sign Up" 클릭
3. GitHub 계정으로 로그인 (권장)
   - GitHub로 연동하면 저장소 접근이 더 쉬워집니다

### 2. 새 프로젝트 생성

1. Vercel 대시보드에서 "Add New..." 클릭
2. "Project" 선택
3. GitHub 저장소 목록에서 프로젝트 선택

## GitHub 저장소 연동

### Vercel GitHub 앱 설치

1. "Import Git Repository" 섹션에서 GitHub 선택
2. 저장소 접근 권한 설정:
   - "All repositories" 또는
   - "Only select repositories" (algoitny 저장소 선택)
3. "Install" 클릭
4. 저장소 목록에서 `algoitny` 선택
5. "Import" 클릭

### 프로젝트 루트 디렉토리 설정

Vercel이 자동으로 `frontend` 디렉토리를 감지하지 못할 수 있으므로:

1. "Root Directory" 설정에서 `frontend` 입력
2. 또는 "Edit" 버튼을 클릭하여 `frontend` 선택

## 환경 변수 설정

### 프로덕션 환경 변수

1. Vercel 프로젝트 설정 페이지에서 "Settings" 탭 클릭
2. 왼쪽 메뉴에서 "Environment Variables" 선택
3. 다음 환경 변수 추가:

#### 필수 환경 변수

| 변수 이름 | 값 | 환경 |
|----------|---|------|
| `VITE_API_URL` | `https://api.testcase.run/api` | Production |
| `VITE_ENV` | `production` | Production |

#### 환경 변수 추가 방법

1. "Key" 필드에 변수 이름 입력 (예: `VITE_API_URL`)
2. "Value" 필드에 값 입력 (예: `https://api.testcase.run/api`)
3. Environment 선택:
   - **Production**: 프로덕션 배포에만 적용
   - **Preview**: PR 및 브랜치 배포에 적용
   - **Development**: `vercel dev` 로컬 개발 시 적용
4. "Save" 클릭

### 프리뷰 환경 변수 (선택사항)

PR 및 브랜치 배포를 위한 별도 환경 변수 설정 가능:

| 변수 이름 | 값 | 환경 |
|----------|---|------|
| `VITE_API_URL` | `https://api-staging.testcase.run/api` | Preview |
| `VITE_ENV` | `preview` | Preview |

> **참고**: Preview 환경 변수를 설정하지 않으면 Production 환경 변수가 사용됩니다.

## 빌드 설정

### 자동 감지 설정 (권장)

Vercel은 `package.json`을 분석하여 자동으로 설정을 감지합니다:

- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 수동 설정

자동 감지가 작동하지 않으면 수동으로 설정:

1. "Settings" > "General" 이동
2. "Build & Development Settings" 섹션에서:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 고급 빌드 설정

#### Node.js 버전 지정

`package.json`에 Node.js 버전을 명시하는 것이 좋습니다:

```json
{
  "engines": {
    "node": ">=18.0.0"
  }
}
```

#### 빌드 성능 최적화

환경 변수로 빌드 성능 개선 가능:

| 변수 이름 | 값 | 설명 |
|----------|---|------|
| `VITE_BUILD_SOURCEMAP` | `false` | 소스맵 생성 비활성화 (빌드 속도 향상) |
| `NODE_OPTIONS` | `--max-old-space-size=4096` | Node.js 메모리 증가 |

## 배포 프로세스

### 자동 배포

GitHub 연동 후 자동 배포가 활성화됩니다:

1. **메인 브랜치 푸시** → 프로덕션 배포
   ```bash
   git push origin main
   ```

2. **PR 생성/업데이트** → 프리뷰 배포
   ```bash
   git checkout -b feature/new-feature
   git push origin feature/new-feature
   # GitHub에서 PR 생성
   ```

3. **기타 브랜치 푸시** → 프리뷰 배포
   ```bash
   git push origin develop
   ```

### 수동 배포

Vercel 대시보드에서 수동으로 배포:

1. Vercel 대시보드의 프로젝트 페이지로 이동
2. "Deployments" 탭 클릭
3. 우측 상단 "Redeploy" 버튼 클릭
4. 배포할 커밋 선택
5. "Redeploy" 확인

### Vercel CLI를 통한 배포

로컬에서 직접 배포도 가능:

```bash
# Vercel CLI 설치
npm install -g vercel

# 프로젝트 디렉토리로 이동
cd frontend

# 로그인
vercel login

# 프로덕션 배포
vercel --prod

# 프리뷰 배포
vercel
```

## 도메인 설정

### 커스텀 도메인 추가

1. Vercel 프로젝트 페이지에서 "Settings" > "Domains" 이동
2. "Add" 버튼 클릭
3. 도메인 입력 (예: `testcase.run` 또는 `www.testcase.run`)
4. "Add" 클릭

### DNS 설정

#### Vercel 네임서버 사용 (권장)

1. 도메인 등록 업체(예: GoDaddy, Namecheap)에서:
   - 네임서버를 Vercel의 네임서버로 변경:
     ```
     ns1.vercel-dns.com
     ns2.vercel-dns.com
     ```

2. Vercel에서 자동으로 DNS 레코드 관리

#### 기존 DNS 사용

1. 도메인 등록 업체의 DNS 설정에서:
   - **A 레코드** 추가:
     ```
     Type: A
     Name: @
     Value: 76.76.21.21
     ```
   - **CNAME 레코드** 추가 (www 서브도메인):
     ```
     Type: CNAME
     Name: www
     Value: cname.vercel-dns.com
     ```

2. Vercel에서 도메인 소유권 확인 (TXT 레코드 추가 필요할 수 있음)

### SSL 인증서

Vercel은 자동으로 Let's Encrypt SSL 인증서를 생성합니다:
- 도메인 추가 후 자동 발급 (몇 분 소요)
- 자동 갱신
- HTTPS 강제 리다이렉트 기본 활성화

## 프로덕션 vs 프리뷰 배포

### 프로덕션 배포 (Production)

- **트리거**: `main` 브랜치에 푸시
- **도메인**: 프로덕션 도메인 (예: `testcase.run`)
- **환경 변수**: Production 환경 변수 사용
- **API URL**: `https://api.testcase.run/api`
- **특징**:
  - 안정적인 최종 버전
  - 실제 사용자에게 제공
  - 성능 최적화 빌드

### 프리뷰 배포 (Preview)

- **트리거**:
  - Pull Request 생성/업데이트
  - `main` 외 브랜치에 푸시
- **도메인**: 자동 생성된 고유 URL (예: `algoitny-abc123.vercel.app`)
- **환경 변수**: Preview 환경 변수 사용 (없으면 Production 사용)
- **API URL**: 설정에 따라 다름
- **특징**:
  - 각 PR마다 고유한 URL 생성
  - 코드 리뷰 및 테스트용
  - GitHub PR에 자동으로 링크 추가

### 배포 타입 비교

| 항목 | Production | Preview |
|-----|-----------|---------|
| 브랜치 | `main` | 기타 브랜치, PR |
| 도메인 | 프로덕션 도메인 | `*.vercel.app` |
| 목적 | 실서비스 | 테스트/리뷰 |
| 캐싱 | 강력한 CDN 캐싱 | 기본 캐싱 |
| 환경 변수 | Production | Preview 또는 Production |

## 문제 해결 (Troubleshooting)

### 빌드 실패

#### 1. 의존성 설치 실패

**증상**: `npm install` 단계에서 에러 발생

**해결책**:
```bash
# 로컬에서 테스트
rm -rf node_modules package-lock.json
npm install
npm run build

# 성공하면 package-lock.json 커밋
git add package-lock.json
git commit -m "Update package-lock.json"
git push
```

#### 2. 타입스크립트 에러

**증상**: 빌드 중 TS 타입 에러

**해결책**:
- 로컬에서 `npm run build`로 에러 확인
- 타입 에러 수정
- 또는 임시로 `tsconfig.json`에서 `"skipLibCheck": true` 추가

#### 3. 메모리 부족

**증상**: `JavaScript heap out of memory`

**해결책**:
Vercel 환경 변수에 추가:
```
NODE_OPTIONS=--max-old-space-size=4096
```

### 환경 변수 문제

#### 1. API URL이 적용되지 않음

**확인 사항**:
- 환경 변수 이름이 `VITE_` 접두사로 시작하는지 확인
- Vercel 대시보드에서 환경 변수 저장 확인
- 배포 후 재배포 필요 (환경 변수 변경 시)

**해결책**:
```bash
# Vercel CLI로 환경 변수 확인
vercel env ls

# 재배포
vercel --prod
```

#### 2. 환경 변수가 undefined

**증상**: `import.meta.env.VITE_API_URL`이 `undefined`

**해결책**:
- `.env.production` 파일 확인
- Vercel 환경 변수에 올바르게 설정되었는지 확인
- 빌드 로그에서 환경 변수 출력 확인

### 라우팅 문제

#### 1. 새로고침 시 404 에러

**증상**: `/problems` 같은 경로에서 새로고침하면 404

**원인**: SPA 라우팅 미설정

**해결책**:
`vercel.json` 파일 확인:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

#### 2. API 요청 CORS 에러

**증상**: 브라우저 콘솔에 CORS 에러

**해결책**:
- 백엔드 API에서 Vercel 도메인을 CORS 허용 목록에 추가
- 프리뷰 배포의 경우: `*.vercel.app` 와일드카드 추가

### 성능 문제

#### 1. 느린 로딩 속도

**해결책**:
- 이미지 최적화 (WebP 포맷 사용)
- 코드 스플리팅 확인
- Vercel Analytics 활성화하여 성능 모니터링

#### 2. 큰 번들 사이즈

**해결책**:
```bash
# 번들 분석
npm run build -- --mode production

# 빌드 로그에서 번들 크기 확인
# 필요시 dynamic import로 코드 스플리팅
```

### 배포 로그 확인

모든 문제의 첫 단계는 배포 로그 확인:

1. Vercel 대시보드 > "Deployments" 탭
2. 실패한 배포 클릭
3. "Building" 또는 "Deploying" 섹션 확인
4. 에러 메시지 읽고 해결

## 유용한 명령어

### Vercel CLI 명령어

```bash
# 로컬 개발 서버 (Vercel 환경과 동일)
vercel dev

# 환경 변수 관리
vercel env ls                    # 목록 조회
vercel env add VITE_API_URL      # 추가
vercel env rm VITE_API_URL       # 삭제

# 배포 관리
vercel ls                        # 배포 목록
vercel inspect [deployment-url]  # 배포 정보 확인
vercel logs [deployment-url]     # 로그 확인

# 프로젝트 링크
vercel link                      # 로컬 프로젝트와 Vercel 프로젝트 연결
```

### 로컬 테스트

```bash
# 개발 모드 (localhost API 사용)
npm run dev

# 프로덕션 빌드 테스트
npm run build
npm run preview

# 환경 변수 확인
cat .env.development
cat .env.production
```

## 추가 리소스

- [Vercel 공식 문서](https://vercel.com/docs)
- [Vite 배포 가이드](https://vitejs.dev/guide/static-deploy.html)
- [Vercel CLI 문서](https://vercel.com/docs/cli)
- [Vercel 환경 변수 문서](https://vercel.com/docs/environment-variables)

## 체크리스트

배포 전 최종 확인:

- [ ] `.env.development`와 `.env.production` 파일 생성
- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] `vercel.json` 파일 생성 (SPA 라우팅 설정)
- [ ] 로컬에서 `npm run build` 성공
- [ ] Vercel 환경 변수 설정 완료
- [ ] GitHub 저장소 푸시 완료
- [ ] 백엔드 API CORS 설정 확인
- [ ] 도메인 DNS 설정 완료 (커스텀 도메인 사용 시)

## 지원

문제가 해결되지 않으면:

1. Vercel 대시보드의 "Help" 섹션 확인
2. [Vercel 커뮤니티](https://github.com/vercel/vercel/discussions)
3. [Vercel 지원팀](https://vercel.com/support) 문의

---

마지막 업데이트: 2025-10-06
