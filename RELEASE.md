# AlgoItny Backend Release Guide

## 🚀 빠른 릴리스

```bash
# 1. 변경사항 커밋
git add .
git commit -m "feat: add new feature"

# 2. 버전 태그 생성 (v로 시작해야 함!)
git tag v1.0.0

# 3. 릴리스 실행 (git tag push + multi-arch build + ECR push + manifest 생성)
make release
```

## 📋 Release 명령어

### `make release` - 전체 릴리스 프로세스

다음 작업을 자동으로 수행합니다:

1. **Git Tag 검증**
   - 현재 커밋에 tag가 있는지 확인
   - Tag가 `v`로 시작하는지 검증 (v1.0.0, v2.3.1 등)

2. **Release Notes 생성**
   - 이전 버전과의 차이 분석
   - 변경된 커밋 목록 표시
   - 통계 정보 (커밋 수, 변경된 파일 수, 작성자 수)

3. **Git Tag Push**
   - Remote에 tag 존재 여부 확인
   - 이미 존재하면 덮어쓰기 여부 확인
   - Tag를 origin에 push

4. **멀티 아키텍처 빌드**
   - Docker Buildx 설정
   - `linux/amd64`, `linux/arm64` 동시 빌드
   - 3개의 태그로 ECR에 push:
     - `v1.0.0` (버전 태그)
     - `latest` (최신)
     - `abc123` (git commit hash)

5. **Manifest 검증**
   - Multi-arch manifest 생성 확인
   - 각 아키텍처별 이미지 확인

6. **배포 가이드 출력**
   - Helm 배포 명령어
   - Kubernetes 확인 명령어

## 🔧 사전 요구사항

### 1. Docker Buildx

Docker Desktop을 사용하면 자동으로 설치되어 있습니다.

```bash
# Buildx 확인
docker buildx version

# Builder 목록
docker buildx ls
```

### 2. AWS CLI 설정

```bash
# AWS 계정 설정
aws configure

# 설정 확인
aws sts get-caller-identity
```

### 3. ECR Repository

ECR repository가 이미 생성되어 있어야 합니다.

```bash
# Repository 확인
aws ecr describe-repositories --repository-names algoitny-backend --region ap-northeast-2
```

## 📝 상세 사용법

### 1. 새로운 릴리스 준비

```bash
# 변경사항 확인
git status
git diff

# 변경사항 커밋
git add .
git commit -m "feat: implement user authentication"

# 현재 상태 확인
git log --oneline -5
```

### 2. 버전 태그 생성

**Semantic Versioning 규칙:**
- `v1.0.0` → `v1.0.1`: 버그 수정 (Patch)
- `v1.0.0` → `v1.1.0`: 새 기능 추가 (Minor)
- `v1.0.0` → `v2.0.0`: Breaking changes (Major)

```bash
# 패치 버전
git tag v1.0.1

# 마이너 버전
git tag v1.1.0

# 메이저 버전
git tag v2.0.0

# Tag 확인
git tag -l
git describe --exact-match --tags HEAD
```

### 3. 릴리스 실행

```bash
# 전체 릴리스 프로세스
make release
```

**실행 과정:**

```
🚀 AlgoItny Backend Release
════════════════════════════════════════════════════════════════

🏷️  Release Version: v1.0.0

📝 Release notes를 생성합니다...

════════════════════════════════════════════════════════════════
📋 Release Notes: v1.0.0
════════════════════════════════════════════════════════════════

📦 Changes since v0.9.0:

abc1234 feat: add user authentication
def5678 fix: resolve database connection issue
ghi9012 docs: update API documentation

📊 Statistics:
  Commits: 3
  Files changed: 15
  Authors: 2

════════════════════════════════════════════════════════════════

Release notes를 확인하셨나요? 계속하시겠습니까? (y/N) y

📤 Step 1/4: Git tag를 push합니다...
✅ Tag push 완료: v1.0.0

🔨 Step 2/4: 멀티 아키텍처 이미지를 빌드하고 ECR에 푸시합니다...

📦 Build Information:
  Version: v1.0.0
  Commit: abc1234
  Date: 2025-10-06T12:00:00Z
  Platforms: linux/amd64, linux/arm64

[+] Building 120.5s (15/15) FINISHED
...

✅ 멀티 아키텍처 이미지 빌드 및 푸시 완료!

📋 Pushed Images:
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:latest
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:abc1234

🏗️  Architectures: linux/amd64, linux/arm64

🔍 Step 3/4: Manifest를 검증합니다...

📋 Manifest for ...:v1.0.0:
Name:      123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0
MediaType: application/vnd.docker.distribution.manifest.list.v2+json
Digest:    sha256:...

Manifests:
  Name:      ...@sha256:...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/amd64

  Name:      ...@sha256:...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/arm64

📊 Step 4/4: 이미지 정보를 확인합니다...

════════════════════════════════════════════════════════════════
✅ Release 완료!
════════════════════════════════════════════════════════════════

🎯 Released Version: v1.0.0
📦 Image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0
🏗️  Architectures: linux/amd64, linux/arm64

📝 다음 단계:

  1. EKS에 배포:
     cd nest
     helm upgrade --install algoitny-backend . \
       --values values-production.yaml \
       --set image.tag=v1.0.0

  2. 배포 확인:
     kubectl get pods -l app.kubernetes.io/name=algoitny-backend
     kubectl get ingress algoitny-backend

  3. 로그 확인:
     kubectl logs -l app.kubernetes.io/component=gunicorn --tail=100
```

## 🔍 개별 단계 실행

필요시 각 단계를 개별적으로 실행할 수 있습니다:

```bash
# 1. Git tag 검증만
make check-git-tag

# 2. Release notes 생성만
make generate-release-notes

# 3. Git tag push만
make push-git-tag

# 4. 멀티 아키텍처 빌드만
make build-multiarch

# 5. Manifest 검증만
make verify-manifest

# 6. ECR 이미지 목록
make ecr-list

# 7. 이미지 상세 정보
make ecr-info
```

## ⚠️ 주의사항

### Tag 형식

**올바른 형식:**
```bash
git tag v1.0.0   ✅
git tag v2.3.1   ✅
git tag v10.0.0  ✅
```

**잘못된 형식:**
```bash
git tag 1.0.0    ❌ (v가 없음)
git tag ver1.0   ❌ (v 뒤에 숫자가 아님)
git tag release  ❌ (버전 형식이 아님)
```

에러 발생시:
```
❌ Error: Tag는 'v'로 시작해야 합니다. (현재: 1.0.0)
💡 올바른 형식: v1.0.0, v1.2.3
```

### Tag가 없을 때

```
❌ Error: 현재 커밋에 tag가 없습니다.
💡 Tag를 생성하세요: git tag v1.0.0
```

### Docker Buildx 없을 때

```
❌ Error: Docker buildx가 설치되어 있지 않습니다.
💡 Docker Desktop을 사용하거나 buildx를 설치하세요.
```

## 🔄 릴리스 취소/롤백

### 릴리스 전 취소

Release notes 확인 단계에서 `N`을 입력하면 취소됩니다.

### Git Tag 삭제

```bash
# 로컬 tag 삭제
git tag -d v1.0.0

# Remote tag 삭제
git push origin :refs/tags/v1.0.0
```

### ECR 이미지 삭제

```bash
# 특정 태그 삭제
aws ecr batch-delete-image \
  --repository-name algoitny-backend \
  --image-ids imageTag=v1.0.0 \
  --region ap-northeast-2
```

## 📊 릴리스 확인

### ECR 이미지 목록

```bash
make ecr-list
```

### Manifest 확인

```bash
# 특정 버전의 manifest
docker buildx imagetools inspect \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0

# latest manifest
docker buildx imagetools inspect \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:latest
```

### Git Tags 확인

```bash
# 모든 tag 목록
git tag -l

# 최신 tag
git describe --tags --abbrev=0

# Tag 정보
git show v1.0.0
```

## 🐛 트러블슈팅

### 1. ECR 로그인 실패

```bash
# AWS 설정 확인
aws sts get-caller-identity

# 수동 ECR 로그인
make ecr-login
```

### 2. Buildx builder 오류

```bash
# Builder 재생성
docker buildx rm algoitny-builder
make setup-buildx
```

### 3. Git tag 충돌

Tag가 이미 존재하면 덮어쓰기 여부를 묻습니다:

```
⚠️  Warning: Tag v1.0.0가 이미 remote에 존재합니다.
덮어쓰시겠습니까? (y/N)
```

### 4. 빌드 실패

```bash
# 로그 확인
docker buildx build --progress=plain ...

# 캐시 없이 빌드
docker buildx build --no-cache ...
```

## 💡 팁

### 1. Release Notes 미리 보기

```bash
# 릴리스 실행하지 않고 release notes만 확인
make generate-release-notes
```

### 2. Dry Run

```bash
# Tag는 push하지 않고 로컬에서만 테스트
git tag v1.0.0
make check-git-tag
make generate-release-notes
# 필요시 tag 삭제: git tag -d v1.0.0
```

### 3. 빠른 패치 릴리스

```bash
# 한 줄로 실행
git add . && git commit -m "fix: critical bug" && git tag v1.0.1 && make release
```

## 📚 참고 자료

- [Semantic Versioning](https://semver.org/)
- [Docker Buildx](https://docs.docker.com/buildx/working-with-buildx/)
- [AWS ECR Multi-Architecture](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-multi-architecture-image.html)
