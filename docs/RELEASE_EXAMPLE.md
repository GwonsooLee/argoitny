# AlgoItny Backend - Release 예시

## 시나리오: v1.0.0 릴리스

### 1. 코드 변경 및 커밋

```bash
# 변경사항 확인
git status
git diff

# 커밋
git add .
git commit -m "feat: add user authentication system"
```

### 2. 버전 태그 생성

```bash
# v1.0.0 태그 생성
git tag v1.0.0

# 태그 확인
git tag -l
git describe --exact-match --tags HEAD
```

### 3. 릴리스 실행

```bash
make release
```

### 4. 실행 결과 예시

```
════════════════════════════════════════════════════════════════
🚀 AlgoItny Backend Release
════════════════════════════════════════════════════════════════

🏷️  Release Version: v1.0.0

📝 Release notes를 생성합니다...

════════════════════════════════════════════════════════════════
📋 Release Notes: v1.0.0
════════════════════════════════════════════════════════════════

🎉 Initial Release

Changes:
bae63a2 fix design
f90f1af add more
b32c0ce init

════════════════════════════════════════════════════════════════

Release notes를 확인하셨나요? 계속하시겠습니까? (y/N) y

📤 Step 1/4: Git tag를 push합니다...
✅ Tag push 완료: v1.0.0

🔨 Step 2/4: 멀티 아키텍처 이미지를 빌드하고 ECR에 푸시합니다...
🔧 Buildx builder를 설정합니다...
✅ Buildx builder 준비 완료
🔐 ECR에 로그인합니다...
✅ ECR 로그인 완료
🔨 멀티 아키텍처 이미지를 빌드합니다...

📦 Build Information:
  Version: v1.0.0
  Commit: bae63a2
  Date: 2025-10-06T12:00:00Z
  Platforms: linux/amd64, linux/arm64

[+] Building 120.5s (32/32) FINISHED
 => [linux/amd64 internal] load build definition from Dockerfile
 => [linux/arm64 internal] load build definition from Dockerfile
 ...
 => => pushing manifest for 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0

✅ 멀티 아키텍처 이미지 빌드 및 푸시 완료!

📋 Pushed Images:
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:latest
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:bae63a2

🏗️  Architectures: linux/amd64, linux/arm64

🔍 Step 3/4: Manifest를 검증합니다...

📋 Manifest for 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0:
Name:      123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:v1.0.0
MediaType: application/vnd.docker.distribution.manifest.list.v2+json
Digest:    sha256:abc123...

Manifests:
  Name:      123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend@sha256:def456...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/amd64

  Name:      123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend@sha256:ghi789...
  MediaType: application/vnd.docker.distribution.manifest.v2+json
  Platform:  linux/arm64

📋 Manifest for 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/algoitny-backend:latest:
...

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

### 5. EKS에 배포

```bash
cd nest

# Helm으로 배포
helm upgrade --install algoitny-backend . \
  --values values-production.yaml \
  --set image.tag=v1.0.0

# 배포 상태 확인
kubectl get pods -l app.kubernetes.io/name=algoitny-backend
kubectl get ingress algoitny-backend

# 로그 확인
kubectl logs -l app.kubernetes.io/component=gunicorn --tail=100
```

## 에러 시나리오

### 에러 1: Tag가 v로 시작하지 않음

```bash
git tag 1.0.0
make release
```

**결과:**
```
🔍 Git tag를 검증합니다...
❌ Error: Tag는 'v'로 시작해야 합니다. (현재: 1.0.0)
💡 올바른 형식: v1.0.0, v1.2.3
```

**해결:**
```bash
git tag -d 1.0.0
git tag v1.0.0
```

### 에러 2: Tag가 없음

```bash
# Tag 없이 실행
make release
```

**결과:**
```
🔍 Git tag를 검증합니다...
❌ Error: 현재 커밋에 tag가 없습니다.
💡 Tag를 생성하세요: git tag v1.0.0
```

**해결:**
```bash
git tag v1.0.0
```

### 에러 3: Tag가 이미 존재

```bash
make release
```

**결과:**
```
📤 Git tag를 push합니다: v1.0.0
⚠️  Warning: Tag v1.0.0가 이미 remote에 존재합니다.
덮어쓰시겠습니까? (y/N)
```

**선택:**
- `y`: 기존 tag를 삭제하고 새로 push
- `n`: 릴리스 취소

## 빠른 명령어

```bash
# 한 줄로 전체 프로세스
git add . && git commit -m "feat: new feature" && git tag v1.0.0 && make release

# Release notes만 미리 보기
make generate-release-notes

# ECR 이미지 목록 확인
make ecr-list

# Manifest 검증
make verify-manifest
```

## 버전 관리 예시

```bash
# v1.0.0 → v1.0.1 (버그 수정)
git tag v1.0.1
make release

# v1.0.1 → v1.1.0 (새 기능)
git tag v1.1.0
make release

# v1.1.0 → v2.0.0 (Breaking change)
git tag v2.0.0
make release
```
