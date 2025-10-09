.PHONY: help up down restart logs logs-backend logs-frontend logs-mysql ps clean build stop start frontend-deploy frontend-build s3-upload cf-invalidate cf-status

# Default target
help:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🚀 AlgoItny - 사용 가능한 명령어"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 개발 환경:"
	@echo "  make up           - 모든 서비스 시작 (백그라운드)"
	@echo "  make down         - 모든 서비스 중지 및 제거"
	@echo "  make restart      - 프론트엔드, 백엔드, 워커 재시작 (LocalStack 제외)"
	@echo "  make stop         - 모든 서비스 중지 (제거하지 않음)"
	@echo "  make start        - 중지된 서비스 다시 시작"
	@echo "  make build        - 이미지 다시 빌드 후 시작"
	@echo ""
	@echo "📋 로그 & 상태:"
	@echo "  make logs         - 모든 서비스 로그 보기 (실시간)"
	@echo "  make logs-backend - 백엔드 로그만 보기"
	@echo "  make logs-frontend- 프론트엔드 로그만 보기"
	@echo "  make logs-mysql   - MySQL 로그만 보기"
	@echo "  make ps           - 실행 중인 컨테이너 상태 확인"
	@echo ""
	@echo "🐚 쉘 접속:"
	@echo "  make shell-backend - 백엔드 컨테이너 쉘 접속"
	@echo "  make shell-frontend- 프론트엔드 컨테이너 쉘 접속"
	@echo "  make shell-mysql  - MySQL 컨테이너 쉘 접속"
	@echo ""
	@echo "🗄️  Django:"
	@echo "  make migrate      - Django 마이그레이션 실행"
	@echo "  make makemigrations- Django 마이그레이션 파일 생성"
	@echo ""
	@echo "🗄️  DynamoDB:"
	@echo "  make dynamodb-help - DynamoDB 명령어 도움말"
	@echo "  make dynamodb-init - DynamoDB 테이블 초기화"
	@echo "  make dynamodb-migrate - MySQL → DynamoDB 마이그레이션"
	@echo ""
	@echo "🧪 테스트:"
	@echo "  make test         - 모든 테스트 실행"
	@echo "  make test-cov     - 커버리지 리포트 포함"
	@echo "  make test-help    - 테스트 명령어 도움말"
	@echo ""
	@echo "🚀 프로덕션 릴리스 (ECR):"
	@echo "  make release      - 🌟 전체 릴리스 (git tag push + multi-arch build + ECR push)"
	@echo "  make ecr-help     - ECR 명령어 도움말"
	@echo "  make ecr-list     - ECR 이미지 목록"
	@echo ""
	@echo "☸️  Helm 배포 (EKS):"
	@echo "  make deploy       - 🌟 EKS에 배포 (Helm)"
	@echo "  make k8s-status   - 배포 상태 확인"
	@echo "  make k8s-logs     - 애플리케이션 로그 확인"
	@echo "  make k8s-rollback - 이전 버전으로 롤백"
	@echo "  make helm-dry-run - Dry-run (배포 미리보기)"
	@echo "  make helm-diff    - 현재 배포와 비교 (플러그인 필요)"
	@echo ""
	@echo "🌐 CloudFront 배포:"
	@echo "  make frontend-deploy - 🌟 프론트엔드 빌드 & CloudFront 배포"
	@echo "  make frontend-build  - 프론트엔드 빌드만"
	@echo "  make s3-upload       - S3에 업로드"
	@echo "  make cf-invalidate   - CloudFront 캐시 무효화"
	@echo ""
	@echo "🧹 정리:"
	@echo "  make clean        - 모든 컨테이너, 볼륨, 이미지 제거 (주의!)"
	@echo "  make ecr-clean    - 로컬 ECR 이미지 제거"
	@echo "  make k8s-undeploy - 배포 삭제"
	@echo ""
	@echo "💡 팁:"
	@echo "  릴리스 가이드: cat docs/RELEASE.md"
	@echo "  배포 가이드: cat docs/DEPLOYMENT.md"
	@echo "  최적화 가이드: cat docs/DOCKER_OPTIMIZATION.md"
	@echo ""
	@echo "📝 전체 워크플로우:"
	@echo "  Backend:"
	@echo "    1. make release              # 이미지 빌드 & ECR push"
	@echo "    2. make deploy VERSION=v1.0.0  # EKS에 배포"
	@echo "    3. make k8s-status           # 배포 확인"
	@echo ""
	@echo "  Frontend:"
	@echo "    make frontend-deploy         # 빌드 & CloudFront 배포"
	@echo "════════════════════════════════════════════════════════════════"

# 서비스 시작/중지
up:
	@echo "🚀 모든 서비스를 시작합니다..."
	docker-compose up -d
	@echo "✅ 서비스가 시작되었습니다!"
	@echo "   - 프론트엔드: http://localhost:5173"
	@echo "   - 백엔드 API: http://localhost:8000"
	@echo "   - MySQL: localhost:3306"

down:
	@echo "🛑 모든 서비스를 중지합니다..."
	docker-compose down
	@echo "✅ 서비스가 중지되었습니다."

stop:
	@echo "⏸️  모든 서비스를 일시 중지합니다..."
	docker-compose stop
	@echo "✅ 서비스가 중지되었습니다."

start:
	@echo "▶️  중지된 서비스를 다시 시작합니다..."
	docker-compose start
	@echo "✅ 서비스가 시작되었습니다!"

restart:
	@echo "🔄 프론트엔드, 백엔드, 워커를 재시작합니다..."
	docker-compose restart frontend backend celery-worker-1 celery-worker-2 celery-worker-3
	@echo "✅ 모든 서비스가 재시작되었습니다!"

restart-backend:
	@echo "🔄 백엔드를 재시작합니다..."
	docker-compose restart backend
	@echo "✅ 백엔드가 재시작되었습니다!"

restart-frontend:
	@echo "🔄 프론트엔드를 재시작합니다..."
	docker-compose restart frontend
	@echo "✅ 프론트엔드가 재시작되었습니다!"

# 빌드
build:
	@echo "🔨 이미지를 다시 빌드하고 시작합니다..."
	docker-compose up -d --build
	@echo "✅ 빌드 및 시작이 완료되었습니다!"

rebuild:
	@echo "🔨 모든 것을 처음부터 다시 빌드합니다..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ 재빌드가 완료되었습니다!"

# 로그 확인
logs:
	@echo "📋 모든 서비스의 로그를 표시합니다 (Ctrl+C로 종료)..."
	docker-compose logs -f

logs-backend:
	@echo "📋 백엔드 로그를 표시합니다 (Ctrl+C로 종료)..."
	docker-compose logs -f backend

logs-frontend:
	@echo "📋 프론트엔드 로그를 표시합니다 (Ctrl+C로 종료)..."
	docker-compose logs -f frontend

logs-mysql:
	@echo "📋 MySQL 로그를 표시합니다 (Ctrl+C로 종료)..."
	docker-compose logs -f mysql

# 상태 확인
ps:
	@echo "📊 실행 중인 컨테이너 상태:"
	@docker-compose ps

status: ps

# 쉘 접속
shell-backend:
	@echo "🐚 백엔드 컨테이너 쉘에 접속합니다..."
	docker-compose exec backend sh

shell-frontend:
	@echo "🐚 프론트엔드 컨테이너 쉘에 접속합니다..."
	docker-compose exec frontend sh

shell-mysql:
	@echo "🐚 MySQL 쉘에 접속합니다..."
	docker-compose exec mysql mysql -uroot -prootpassword algoitny

# Django 관련
migrate:
	@echo "🔄 Django 마이그레이션을 실행합니다..."
	docker-compose exec backend python manage.py migrate
	@echo "✅ 마이그레이션이 완료되었습니다!"

makemigrations:
	@echo "📝 Django 마이그레이션 파일을 생성합니다..."
	docker-compose exec backend python manage.py makemigrations
	@echo "✅ 마이그레이션 파일이 생성되었습니다!"

createsuperuser:
	@echo "👤 Django 슈퍼유저를 생성합니다..."
	docker-compose exec backend python manage.py createsuperuser

# DynamoDB 관련
dynamodb-init:
	@echo "🚀 DynamoDB 테이블을 초기화합니다..."
	docker-compose exec backend python scripts/init_dynamodb.py
	@echo "✅ DynamoDB 테이블이 초기화되었습니다!"

dynamodb-migrate:
	@echo "🔄 MySQL에서 DynamoDB로 데이터를 마이그레이션합니다..."
	@read -p "⚠️  이 작업은 시간이 걸릴 수 있습니다. 계속하시겠습니까? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity all --batch-size 25; \
	else \
		echo "❌ 마이그레이션 취소됨"; \
	fi

dynamodb-migrate-dry-run:
	@echo "🧪 DynamoDB 마이그레이션 Dry Run (실제 마이그레이션 없음)..."
	docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity all --dry-run

dynamodb-migrate-users:
	@echo "🔄 사용자 데이터만 마이그레이션합니다..."
	docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity user --batch-size 25

dynamodb-migrate-problems:
	@echo "🔄 문제 데이터만 마이그레이션합니다..."
	docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity problem --batch-size 25

dynamodb-migrate-history:
	@echo "🔄 검색 기록만 마이그레이션합니다..."
	docker-compose exec backend python scripts/migrate_to_dynamodb.py --entity history --batch-size 25

dynamodb-verify:
	@echo "🔍 DynamoDB 마이그레이션을 검증합니다..."
	docker-compose exec backend python scripts/verify_migration.py

dynamodb-help:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🗄️  AlgoItny - DynamoDB 명령어"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 초기화:"
	@echo "  make dynamodb-init          - DynamoDB 테이블 생성"
	@echo ""
	@echo "🔄 마이그레이션:"
	@echo "  make dynamodb-migrate       - 전체 데이터 마이그레이션 (MySQL → DynamoDB)"
	@echo "  make dynamodb-migrate-dry-run - Dry run (실제 마이그레이션 없음)"
	@echo "  make dynamodb-migrate-users - 사용자 데이터만"
	@echo "  make dynamodb-migrate-problems - 문제 데이터만"
	@echo "  make dynamodb-migrate-history - 검색 기록만"
	@echo ""
	@echo "🔍 검증:"
	@echo "  make dynamodb-verify        - 마이그레이션 검증"
	@echo ""
	@echo "💡 팁:"
	@echo "  1. 먼저 테이블을 초기화하세요: make dynamodb-init"
	@echo "  2. Dry run으로 테스트: make dynamodb-migrate-dry-run"
	@echo "  3. 전체 마이그레이션: make dynamodb-migrate"
	@echo "  4. 검증: make dynamodb-verify"
	@echo "════════════════════════════════════════════════════════════════"

# 정리
clean:
	@echo "⚠️  모든 컨테이너, 볼륨, 이미지를 제거합니다!"
	@echo "   이 작업은 되돌릴 수 없습니다. 5초 후 진행됩니다..."
	@sleep 5
	docker-compose down -v --rmi all
	@echo "✅ 정리가 완료되었습니다."

clean-volumes:
	@echo "🗑️  볼륨을 제거합니다 (데이터베이스 데이터 삭제)..."
	docker-compose down -v
	@echo "✅ 볼륨이 제거되었습니다."

# 개발 도구
test:
	@echo "🧪 백엔드 테스트를 실행합니다..."
	docker-compose exec backend python -m pytest

test-cov:
	@echo "🧪 테스트를 실행하고 커버리지를 생성합니다..."
	docker-compose exec backend python -m pytest --cov=api --cov-report=term-missing --cov-report=html

test-fast:
	@echo "🧪 빠른 테스트를 실행합니다 (외부 API 제외)..."
	docker-compose exec backend python -m pytest -m "not external_api" --maxfail=1

test-watch:
	@echo "🧪 파일 변경 감지 자동 테스트를 실행합니다..."
	docker-compose exec backend python -m pytest_watch

test-parallel:
	@echo "🧪 병렬 테스트를 실행합니다 (빠른 실행)..."
	docker-compose exec backend python -m pytest -n auto

test-verbose:
	@echo "🧪 상세 출력으로 테스트를 실행합니다..."
	docker-compose exec backend python -m pytest -vv

test-specific:
	@echo "🧪 특정 테스트 파일을 실행합니다..."
	@read -p "테스트 파일명 (예: test_auth.py): " testfile; \
	docker-compose exec backend python -m pytest tests/$$testfile -v

test-local:
	@echo "🧪 로컬에서 테스트를 실행합니다 (Docker 없이)..."
	cd backend && pytest

test-local-cov:
	@echo "🧪 로컬에서 테스트를 실행하고 커버리지를 생성합니다..."
	cd backend && pytest --cov=api --cov-report=term-missing --cov-report=html

test-clean:
	@echo "🧹 테스트 캐시와 커버리지 데이터를 삭제합니다..."
	docker-compose exec backend sh -c "find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"
	docker-compose exec backend sh -c "find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true"
	docker-compose exec backend sh -c "rm -rf htmlcov .coverage coverage.xml"
	@echo "✅ 테스트 캐시 삭제 완료"

test-install:
	@echo "📦 테스트 의존성을 설치합니다..."
	docker-compose exec backend pip install pytest pytest-django pytest-cov pytest-mock pytest-asyncio pytest-xdist factory-boy faker freezegun

test-help:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🧪 AlgoItny - 테스트 명령어"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 기본 테스트:"
	@echo "  make test             - 모든 테스트 실행"
	@echo "  make test-cov         - 커버리지 리포트 포함"
	@echo "  make test-fast        - 빠른 테스트 (외부 API 제외)"
	@echo "  make test-watch       - 파일 변경 감지 자동 테스트"
	@echo "  make test-parallel    - 병렬 테스트 실행"
	@echo "  make test-verbose     - 상세 출력"
	@echo "  make test-specific    - 특정 테스트 파일 실행"
	@echo ""
	@echo "🏠 로컬 테스트 (Docker 없이):"
	@echo "  make test-local       - 로컬 테스트 실행"
	@echo "  make test-local-cov   - 로컬 테스트 + 커버리지"
	@echo ""
	@echo "🧹 정리:"
	@echo "  make test-clean       - 테스트 캐시 삭제"
	@echo ""
	@echo "📦 설치:"
	@echo "  make test-install     - 테스트 의존성 설치"
	@echo ""
	@echo "💡 팁:"
	@echo "  특정 테스트만 실행: make test-specific"
	@echo "  커버리지 리포트: backend/htmlcov/index.html"
	@echo "════════════════════════════════════════════════════════════════"

format:
	@echo "🎨 코드 포맷팅을 실행합니다..."
	docker-compose exec backend black .
	cd frontend && npm run format

# 프로덕션 빌드
prod-build:
	@echo "🏭 프로덕션 빌드를 생성합니다..."
	cd frontend && npm run build
	@echo "✅ 프로덕션 빌드가 완료되었습니다!"

# 전체 재시작 (데이터 유지)
reset:
	@echo "🔄 전체 재시작 (데이터 유지)..."
	$(MAKE) down
	$(MAKE) up
	@echo "✅ 재시작이 완료되었습니다!"

# 완전 초기화 (데이터 삭제)
fresh:
	@echo "⚠️  완전 초기화 (모든 데이터 삭제)..."
	@echo "   5초 후 진행됩니다..."
	@sleep 5
	$(MAKE) clean-volumes
	$(MAKE) build
	$(MAKE) migrate
	@echo "✅ 완전 초기화가 완료되었습니다!"

# ============================================================================
# ECR & Production Deployment
# ============================================================================

# Variables for ECR
AWS_REGION ?= ap-northeast-2
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null)
ECR_REGISTRY ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
ECR_REPOSITORY ?= algoitny
IMAGE_NAME = $(ECR_REGISTRY)/$(ECR_REPOSITORY)
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "latest")
GIT_COMMIT = $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE = $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
DOCKERFILE = backend/Dockerfile
CONTEXT = backend

.PHONY: ecr-help
ecr-help: ## Show ECR deployment help
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🚀 AlgoItny - ECR & Production Deployment"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 ECR Commands:"
	@echo "  make ecr-login        - ECR에 로그인"
	@echo "  make ecr-create       - ECR 레포지토리 생성"
	@echo "  make ecr-build        - Docker 이미지 빌드"
	@echo "  make ecr-push         - ECR에 이미지 푸시"
	@echo "  make ecr-release      - 빌드 + 푸시 (전체 릴리스)"
	@echo "  make ecr-list         - ECR 이미지 목록 보기"
	@echo "  make ecr-scan         - 이미지 취약점 스캔"
	@echo ""
	@echo "🔧 Variables:"
	@echo "  AWS_REGION      = $(AWS_REGION)"
	@echo "  AWS_ACCOUNT_ID  = $(AWS_ACCOUNT_ID)"
	@echo "  ECR_REGISTRY    = $(ECR_REGISTRY)"
	@echo "  ECR_REPOSITORY  = $(ECR_REPOSITORY)"
	@echo "  VERSION         = $(VERSION)"
	@echo "  GIT_COMMIT      = $(GIT_COMMIT)"
	@echo ""
	@echo "💡 Examples:"
	@echo "  make ecr-release VERSION=v1.0.0    # 특정 버전으로 릴리스"
	@echo "  make ecr-release                   # Git tag로 자동 릴리스"
	@echo ""

.PHONY: check-aws
check-aws: ## AWS CLI 설정 확인
	@echo "🔍 AWS 설정을 확인합니다..."
	@if [ -z "$(AWS_ACCOUNT_ID)" ]; then \
		echo "❌ Error: AWS Account ID를 가져올 수 없습니다. AWS CLI를 설정해주세요."; \
		exit 1; \
	fi
	@echo "✅ AWS Account ID: $(AWS_ACCOUNT_ID)"
	@echo "✅ AWS Region: $(AWS_REGION)"

.PHONY: check-docker
check-docker: ## Docker 실행 확인
	@echo "🔍 Docker 상태를 확인합니다..."
	@if ! docker info > /dev/null 2>&1; then \
		echo "❌ Error: Docker가 실행중이 아닙니다."; \
		exit 1; \
	fi
	@echo "✅ Docker가 실행중입니다."

.PHONY: ecr-login
ecr-login: check-aws check-docker ## ECR 로그인
	@echo "🔐 ECR에 로그인합니다..."
	@aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	@echo "✅ ECR 로그인 완료"

.PHONY: ecr-create
ecr-create: check-aws ## ECR 레포지토리 생성
	@echo "📦 ECR 레포지토리를 확인합니다..."
	@aws ecr describe-repositories --repository-names $(ECR_REPOSITORY) --region $(AWS_REGION) > /dev/null 2>&1 || \
		(echo "📦 ECR 레포지토리를 생성합니다: $(ECR_REPOSITORY)" && \
		aws ecr create-repository \
			--repository-name $(ECR_REPOSITORY) \
			--region $(AWS_REGION) \
			--image-scanning-configuration scanOnPush=true \
			--encryption-configuration encryptionType=AES256 \
			--tags Key=Project,Value=AlgoItny Key=ManagedBy,Value=Makefile)
	@echo "✅ ECR 레포지토리 준비 완료"

.PHONY: ecr-build
ecr-build: check-docker ## Docker 이미지 빌드
	@echo "🔨 Docker 이미지를 빌드합니다..."
	@echo "   Version: $(VERSION)"
	@echo "   Commit: $(GIT_COMMIT)"
	@echo "   Build Date: $(BUILD_DATE)"
	@docker build \
		--file $(DOCKERFILE) \
		--tag $(ECR_REPOSITORY):$(VERSION) \
		--tag $(ECR_REPOSITORY):latest \
		--build-arg VERSION=$(VERSION) \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--platform linux/amd64 \
		$(CONTEXT)
	@echo "✅ 이미지 빌드 완료: $(ECR_REPOSITORY):$(VERSION)"

.PHONY: ecr-tag
ecr-tag: ## ECR용 이미지 태그
	@echo "🏷️  ECR용 이미지를 태그합니다..."
	@docker tag $(ECR_REPOSITORY):$(VERSION) $(IMAGE_NAME):$(VERSION)
	@docker tag $(ECR_REPOSITORY):$(VERSION) $(IMAGE_NAME):latest
	@docker tag $(ECR_REPOSITORY):$(VERSION) $(IMAGE_NAME):$(GIT_COMMIT)
	@echo "✅ 태그 완료:"
	@echo "   - $(IMAGE_NAME):$(VERSION)"
	@echo "   - $(IMAGE_NAME):latest"
	@echo "   - $(IMAGE_NAME):$(GIT_COMMIT)"

.PHONY: ecr-push
ecr-push: ecr-login ecr-tag ## ECR에 이미지 푸시
	@echo "📤 ECR에 이미지를 푸시합니다..."
	@docker push $(IMAGE_NAME):$(VERSION)
	@docker push $(IMAGE_NAME):latest
	@docker push $(IMAGE_NAME):$(GIT_COMMIT)
	@echo ""
	@echo "✅ ECR 푸시 완료!"
	@echo ""
	@echo "📋 Image URIs:"
	@echo "   $(IMAGE_NAME):$(VERSION)"
	@echo "   $(IMAGE_NAME):latest"
	@echo "   $(IMAGE_NAME):$(GIT_COMMIT)"

.PHONY: ecr-release
ecr-release: ecr-create ecr-build ecr-push ## 전체 릴리스 (빌드 + 푸시)
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "✅ 릴리스 완료!"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "🎯 Image: $(IMAGE_NAME):$(VERSION)"
	@echo ""
	@echo "📝 다음 단계:"
	@echo "  1. EKS에 배포:"
	@echo "     cd nest"
	@echo "     helm upgrade --install algoitny-backend . \\"
	@echo "       --values values-production.yaml \\"
	@echo "       --set image.tag=$(VERSION)"
	@echo ""
	@echo "  2. 배포 확인:"
	@echo "     kubectl get pods -l app.kubernetes.io/name=algoitny-backend"
	@echo ""

.PHONY: ecr-list
ecr-list: ## ECR 이미지 목록 보기
	@echo "📋 ECR 이미지 목록 ($(ECR_REPOSITORY)):"
	@aws ecr list-images \
		--repository-name $(ECR_REPOSITORY) \
		--region $(AWS_REGION) \
		--query 'imageIds[*].imageTag' \
		--output table

.PHONY: ecr-scan
ecr-scan: ## 이미지 취약점 스캔
	@echo "🔍 이미지 취약점 스캔을 시작합니다..."
	@aws ecr start-image-scan \
		--repository-name $(ECR_REPOSITORY) \
		--image-id imageTag=$(VERSION) \
		--region $(AWS_REGION)
	@echo "✅ 스캔 시작됨. 결과 확인: make ecr-scan-results"

.PHONY: ecr-scan-results
ecr-scan-results: ## 스캔 결과 보기
	@echo "📊 스캔 결과:"
	@aws ecr describe-image-scan-findings \
		--repository-name $(ECR_REPOSITORY) \
		--image-id imageTag=$(VERSION) \
		--region $(AWS_REGION) \
		--query 'imageScanFindings.findingSeverityCounts' \
		--output table

.PHONY: ecr-info
ecr-info: ## 이미지 상세 정보
	@echo "📋 이미지 상세 정보:"
	@aws ecr describe-images \
		--repository-name $(ECR_REPOSITORY) \
		--image-ids imageTag=$(VERSION) \
		--region $(AWS_REGION) \
		--query 'imageDetails[0]' \
		--output table

.PHONY: ecr-clean
ecr-clean: ## 로컬 이미지 제거
	@echo "🗑️  로컬 이미지를 제거합니다..."
	@docker rmi -f $(ECR_REPOSITORY):$(VERSION) 2>/dev/null || true
	@docker rmi -f $(ECR_REPOSITORY):latest 2>/dev/null || true
	@docker rmi -f $(IMAGE_NAME):$(VERSION) 2>/dev/null || true
	@docker rmi -f $(IMAGE_NAME):latest 2>/dev/null || true
	@docker rmi -f $(IMAGE_NAME):$(GIT_COMMIT) 2>/dev/null || true
	@echo "✅ 로컬 이미지 제거 완료"

# ============================================================================
# Production Release (Multi-arch with Manifest)
# ============================================================================

.PHONY: check-git-tag
check-git-tag: ## Git tag 검증 (v로 시작하는지)
	@echo "🔍 Git tag를 검증합니다..."
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	if [ -z "$$CURRENT_TAG" ]; then \
		echo "❌ Error: 현재 커밋에 tag가 없습니다."; \
		echo "💡 Tag를 생성하세요: git tag v1.0.0"; \
		exit 1; \
	fi; \
	if [ "$${CURRENT_TAG#v}" = "$$CURRENT_TAG" ]; then \
		echo "❌ Error: Tag는 'v'로 시작해야 합니다. (현재: $$CURRENT_TAG)"; \
		echo "💡 올바른 형식: v1.0.0, v1.2.3"; \
		exit 1; \
	fi; \
	echo "✅ Git tag: $$CURRENT_TAG"

.PHONY: check-buildx
check-buildx: ## Docker buildx 확인
	@echo "🔍 Docker buildx를 확인합니다..."
	@if ! docker buildx version > /dev/null 2>&1; then \
		echo "❌ Error: Docker buildx가 설치되어 있지 않습니다."; \
		echo "💡 Docker Desktop을 사용하거나 buildx를 설치하세요."; \
		exit 1; \
	fi
	@echo "✅ Docker buildx 사용 가능"
	@docker buildx ls

.PHONY: setup-buildx
setup-buildx: check-buildx ## Buildx builder 설정
	@echo "🔧 Buildx builder를 설정합니다..."
	@docker buildx create --name algoitny-builder --use 2>/dev/null || \
		docker buildx use algoitny-builder 2>/dev/null || \
		docker buildx use default
	@docker buildx inspect --bootstrap
	@echo "✅ Buildx builder 준비 완료"

.PHONY: generate-release-notes
generate-release-notes: ## Release notes 생성
	@echo "📝 Release notes를 생성합니다..."
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	PREV_TAG=$$(git describe --abbrev=0 --tags $$CURRENT_TAG^ 2>/dev/null || echo ""); \
	echo ""; \
	echo "════════════════════════════════════════════════════════════════"; \
	echo "📋 Release Notes: $$CURRENT_TAG"; \
	echo "════════════════════════════════════════════════════════════════"; \
	echo ""; \
	if [ -z "$$PREV_TAG" ]; then \
		echo "🎉 Initial Release"; \
		echo ""; \
		echo "Changes:"; \
		git log --oneline --decorate --no-merges | head -20; \
	else \
		echo "📦 Changes since $$PREV_TAG:"; \
		echo ""; \
		git log $$PREV_TAG..$$CURRENT_TAG --oneline --decorate --no-merges; \
		echo ""; \
		echo "📊 Statistics:"; \
		echo "  Commits: $$(git rev-list --count $$PREV_TAG..$$CURRENT_TAG)"; \
		echo "  Files changed: $$(git diff --shortstat $$PREV_TAG..$$CURRENT_TAG | awk '{print $$1}')"; \
		echo "  Authors: $$(git log $$PREV_TAG..$$CURRENT_TAG --format='%aN' | sort -u | wc -l | tr -d ' ')"; \
	fi; \
	echo ""; \
	echo "════════════════════════════════════════════════════════════════"; \
	echo ""

.PHONY: push-git-tag
push-git-tag: check-git-tag ## Git tag를 remote에 push
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	echo "📤 Git tag를 push합니다: $$CURRENT_TAG"; \
	if git ls-remote --tags origin | grep -q "refs/tags/$$CURRENT_TAG"; then \
		echo "⚠️  Warning: Tag $$CURRENT_TAG가 이미 remote에 존재합니다."; \
		read -p "덮어쓰시겠습니까? (y/N) " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			echo "❌ Tag push 취소됨"; \
			exit 1; \
		fi; \
		git push origin :refs/tags/$$CURRENT_TAG; \
	fi; \
	git push origin $$CURRENT_TAG; \
	echo "✅ Tag push 완료: $$CURRENT_TAG"

.PHONY: build-multiarch
build-multiarch: setup-buildx ecr-login ## 멀티 아키텍처 이미지 빌드 및 푸시
	@echo "🔨 멀티 아키텍처 이미지를 빌드합니다..."
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	GIT_COMMIT=$$(git rev-parse --short HEAD); \
	BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ"); \
	echo ""; \
	echo "📦 Build Information:"; \
	echo "  Version: $$CURRENT_TAG"; \
	echo "  Commit: $$GIT_COMMIT"; \
	echo "  Date: $$BUILD_DATE"; \
	echo "  Platforms: linux/amd64, linux/arm64"; \
	echo ""; \
	cd backend && \
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		--file Dockerfile \
		--build-arg VERSION=$$CURRENT_TAG \
		--build-arg GIT_COMMIT=$$GIT_COMMIT \
		--build-arg BUILD_DATE=$$BUILD_DATE \
		--tag $(IMAGE_NAME):$$CURRENT_TAG \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):$$GIT_COMMIT \
		--push \
		--provenance=false \
		--sbom=false \
		. && \
	cd .. && \
	echo "" && \
	echo "✅ 멀티 아키텍처 이미지 빌드 및 푸시 완료!" && \
	echo "" && \
	echo "📋 Pushed Images:" && \
	echo "  $(IMAGE_NAME):$$CURRENT_TAG" && \
	echo "  $(IMAGE_NAME):latest" && \
	echo "  $(IMAGE_NAME):$$GIT_COMMIT" && \
	echo "" && \
	echo "🏗️  Architectures: linux/amd64, linux/arm64"

.PHONY: verify-manifest
verify-manifest: ## Manifest 검증
	@echo "🔍 Manifest를 검증합니다..."
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	if [ -z "$$CURRENT_TAG" ]; then \
		echo "❌ Error: Git tag를 찾을 수 없습니다."; \
		exit 1; \
	fi; \
	echo ""; \
	echo "📋 Manifest for $(IMAGE_NAME):$$CURRENT_TAG:"; \
	docker buildx imagetools inspect $(IMAGE_NAME):$$CURRENT_TAG; \
	echo ""; \
	echo "📋 Manifest for $(IMAGE_NAME):latest:"; \
	docker buildx imagetools inspect $(IMAGE_NAME):latest

.PHONY: release
release: check-docker check-aws check-git-tag ## 전체 릴리스 프로세스 (이미지 빌드 & ECR push)
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🚀 AlgoItny Backend Release"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	echo "🏷️  Release Version: $$CURRENT_TAG"; \
	echo ""
	@$(MAKE) generate-release-notes
	@echo ""
	@read -p "Release notes를 확인하셨나요? 계속하시겠습니까? (y/N) " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "❌ Release 취소됨"; \
		exit 1; \
	fi
	@echo ""
	@echo "📤 Step 1/3: Git tag를 push합니다..."
	@$(MAKE) push-git-tag
	@echo ""
	@echo "🔨 Step 2/3: 멀티 아키텍처 이미지를 빌드하고 ECR에 푸시합니다..."
	@$(MAKE) build-multiarch
	@echo ""
	@echo "🔍 Step 3/3: Manifest를 검증합니다..."
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	echo ""; \
	echo "📋 Manifest for $(IMAGE_NAME):$$CURRENT_TAG:"; \
	docker buildx imagetools inspect $(IMAGE_NAME):$$CURRENT_TAG; \
	echo ""; \
	echo "📋 Manifest for $(IMAGE_NAME):latest:"; \
	docker buildx imagetools inspect $(IMAGE_NAME):latest
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "✅ Release 완료!"
	@echo "════════════════════════════════════════════════════════════════"
	@CURRENT_TAG=$$(git describe --exact-match --tags HEAD 2>/dev/null); \
	echo ""; \
	echo "🎯 Released Version: $$CURRENT_TAG"; \
	echo "📦 Image: $(IMAGE_NAME):$$CURRENT_TAG"; \
	echo "🏗️  Architectures: linux/amd64, linux/arm64"; \
	echo ""; \
	echo "📝 다음 단계:"; \
	echo ""; \
	echo "  EKS에 배포하려면:"; \
	echo "    make deploy VERSION=$$CURRENT_TAG"; \
	echo ""; \
	echo "  또는 수동으로:"; \
	echo "    cd nest"; \
	echo "    helm upgrade --install algoitny-backend . \\"; \
	echo "      --values values-production.yaml \\"; \
	echo "      --set image.tag=$$CURRENT_TAG"; \
	echo ""

# ============================================================================
# Helm Deployment
# ============================================================================

HELM_RELEASE_NAME ?= algoitny-backend
HELM_NAMESPACE ?= default
HELM_CHART_PATH = nest
HELM_VALUES_FILE ?= values-production.yaml
DEPLOY_VERSION ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "latest")

.PHONY: check-kubectl
check-kubectl: ## kubectl 설정 확인
	@echo "🔍 kubectl 설정을 확인합니다..."
	@if ! kubectl cluster-info > /dev/null 2>&1; then \
		echo "❌ Error: kubectl이 설정되지 않았거나 클러스터에 접근할 수 없습니다."; \
		exit 1; \
	fi
	@CONTEXT=$$(kubectl config current-context); \
	echo "✅ Current Context: $$CONTEXT"

.PHONY: check-helm
check-helm: ## Helm 설치 확인
	@echo "🔍 Helm을 확인합니다..."
	@if ! command -v helm &> /dev/null; then \
		echo "❌ Error: Helm이 설치되어 있지 않습니다."; \
		echo "💡 설치: brew install helm"; \
		exit 1; \
	fi
	@echo "✅ Helm version: $$(helm version --short)"

.PHONY: helm-lint
helm-lint: check-helm ## Helm 차트 검증
	@echo "🔍 Helm 차트를 검증합니다..."
	@cd $(HELM_CHART_PATH) && helm lint . --values $(HELM_VALUES_FILE)
	@echo "✅ Helm 차트 검증 완료"

.PHONY: helm-dry-run
helm-dry-run: check-kubectl check-helm ## Helm dry-run (실제 배포 없이 테스트)
	@echo "🔍 Helm dry-run을 실행합니다..."
	@echo "Version: $(DEPLOY_VERSION)"
	@echo "Namespace: $(HELM_NAMESPACE)"
	@echo "Release: $(HELM_RELEASE_NAME)"
	@echo ""
	@cd $(HELM_CHART_PATH) && \
	helm upgrade --install $(HELM_RELEASE_NAME) . \
		--namespace $(HELM_NAMESPACE) \
		--create-namespace \
		--values $(HELM_VALUES_FILE) \
		--set image.tag=$(DEPLOY_VERSION) \
		--dry-run \
		--debug

.PHONY: helm-template
helm-template: check-helm ## Helm template 렌더링 (manifest 미리보기)
	@echo "📋 Helm template을 렌더링합니다..."
	@echo "Version: $(DEPLOY_VERSION)"
	@echo ""
	@cd $(HELM_CHART_PATH) && \
	helm template $(HELM_RELEASE_NAME) . \
		--namespace $(HELM_NAMESPACE) \
		--values $(HELM_VALUES_FILE) \
		--set image.tag=$(DEPLOY_VERSION)

.PHONY: deploy
deploy: check-kubectl check-helm ## EKS에 배포 (Helm)
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "🚀 AlgoItny Backend Deployment"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@CONTEXT=$$(kubectl config current-context); \
	echo "📦 Deployment Information:"; \
	echo "  Cluster Context: $$CONTEXT"; \
	echo "  Namespace: $(HELM_NAMESPACE)"; \
	echo "  Release: $(HELM_RELEASE_NAME)"; \
	echo "  Version: $(DEPLOY_VERSION)"; \
	echo "  Chart: $(HELM_CHART_PATH)"; \
	echo "  Values: $(HELM_VALUES_FILE)"; \
	echo ""; \
	read -p "위 설정으로 배포하시겠습니까? (y/N) " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "❌ 배포 취소됨"; \
		exit 1; \
	fi
	@echo ""
	@echo "🔍 Step 1/3: Helm 차트 검증..."
	@$(MAKE) helm-lint
	@echo ""
	@echo "🚀 Step 2/3: Helm으로 배포 중..."
	@cd $(HELM_CHART_PATH) && \
	helm upgrade --install $(HELM_RELEASE_NAME) . \
		--namespace $(HELM_NAMESPACE) \
		--create-namespace \
		--values $(HELM_VALUES_FILE) \
		--set image.tag=$(DEPLOY_VERSION) \
		--wait \
		--timeout 10m
	@echo ""
	@echo "✅ Helm 배포 완료!"
	@echo ""
	@echo "📊 Step 3/3: 배포 상태 확인..."
	@$(MAKE) k8s-status
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "✅ 배포 완료!"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📝 유용한 명령어:"
	@echo "  make k8s-status    - 배포 상태 확인"
	@echo "  make k8s-logs      - 로그 확인"
	@echo "  make k8s-rollback  - 이전 버전으로 롤백"
	@echo ""

.PHONY: k8s-status
k8s-status: check-kubectl ## 배포 상태 확인
	@echo "📊 배포 상태를 확인합니다..."
	@echo ""
	@echo "=== Pods ==="
	@kubectl get pods -n $(HELM_NAMESPACE) -l app.kubernetes.io/name=algoitny-backend
	@echo ""
	@echo "=== Services ==="
	@kubectl get svc -n $(HELM_NAMESPACE) -l app.kubernetes.io/name=algoitny-backend
	@echo ""
	@echo "=== Ingress ==="
	@kubectl get ingress -n $(HELM_NAMESPACE) $(HELM_RELEASE_NAME) 2>/dev/null || echo "No ingress found"
	@echo ""
	@echo "=== HPA ==="
	@kubectl get hpa -n $(HELM_NAMESPACE) 2>/dev/null || echo "No HPA found"
	@echo ""
	@echo "=== KEDA ScaledObject ==="
	@kubectl get scaledobject -n $(HELM_NAMESPACE) 2>/dev/null || echo "No ScaledObject found"

.PHONY: k8s-logs
k8s-logs: check-kubectl ## 애플리케이션 로그 확인
	@echo "📋 로그를 확인합니다..."
	@echo ""
	@echo "어떤 컴포넌트의 로그를 보시겠습니까?"
	@echo "  1) Gunicorn (Django API)"
	@echo "  2) Celery Worker"
	@echo "  3) Celery Beat"
	@echo "  4) All"
	@read -p "선택 (1-4): " choice; \
	case $$choice in \
		1) kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=gunicorn --tail=100 -f ;; \
		2) kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=celery-worker --tail=100 -f ;; \
		3) kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=celery-beat --tail=100 -f ;; \
		4) kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/name=algoitny-backend --tail=100 -f ;; \
		*) echo "잘못된 선택입니다." ;; \
	esac

.PHONY: k8s-logs-gunicorn
k8s-logs-gunicorn: check-kubectl ## Gunicorn 로그만 확인
	@kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=gunicorn --tail=100 -f

.PHONY: k8s-logs-celery
k8s-logs-celery: check-kubectl ## Celery Worker 로그만 확인
	@kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=celery-worker --tail=100 -f

.PHONY: k8s-logs-beat
k8s-logs-beat: check-kubectl ## Celery Beat 로그만 확인
	@kubectl logs -n $(HELM_NAMESPACE) -l app.kubernetes.io/component=celery-beat --tail=100 -f

.PHONY: helm-history
helm-history: check-helm ## Helm 배포 히스토리
	@echo "📜 Helm 배포 히스토리:"
	@helm history $(HELM_RELEASE_NAME) -n $(HELM_NAMESPACE)

.PHONY: k8s-rollback
k8s-rollback: check-kubectl check-helm ## 이전 버전으로 롤백
	@echo "🔄 롤백할 revision을 확인합니다..."
	@echo ""
	@helm history $(HELM_RELEASE_NAME) -n $(HELM_NAMESPACE)
	@echo ""
	@read -p "롤백할 revision 번호를 입력하세요 (0=이전 버전): " revision; \
	if [ "$$revision" = "0" ]; then \
		echo "이전 버전으로 롤백합니다..."; \
		helm rollback $(HELM_RELEASE_NAME) -n $(HELM_NAMESPACE) --wait; \
	else \
		echo "Revision $$revision으로 롤백합니다..."; \
		helm rollback $(HELM_RELEASE_NAME) $$revision -n $(HELM_NAMESPACE) --wait; \
	fi
	@echo "✅ 롤백 완료"
	@$(MAKE) k8s-status

.PHONY: k8s-undeploy
k8s-undeploy: check-kubectl check-helm ## 배포 삭제
	@echo "⚠️  WARNING: $(HELM_RELEASE_NAME)를 삭제합니다!"
	@read -p "정말로 삭제하시겠습니까? (yes/N) " -r; \
	echo; \
	if [[ $$REPLY = "yes" ]]; then \
		helm uninstall $(HELM_RELEASE_NAME) -n $(HELM_NAMESPACE); \
		echo "✅ 삭제 완료"; \
	else \
		echo "❌ 삭제 취소됨"; \
	fi

.PHONY: helm-diff
helm-diff: check-kubectl check-helm ## 현재 배포와 새 버전 비교 (helm-diff 플러그인 필요)
	@if ! helm plugin list | grep -q diff; then \
		echo "⚠️  helm-diff 플러그인이 설치되어 있지 않습니다."; \
		echo "💡 설치: helm plugin install https://github.com/databus23/helm-diff"; \
		exit 1; \
	fi
	@echo "🔍 변경사항을 비교합니다..."
	@cd $(HELM_CHART_PATH) && \
	helm diff upgrade $(HELM_RELEASE_NAME) . \
		--namespace $(HELM_NAMESPACE) \
		--values $(HELM_VALUES_FILE) \
		--set image.tag=$(DEPLOY_VERSION)

# ============================================================================
# CloudFront Deployment
# ============================================================================

CLOUDFRONT_ID ?= E2FHGERNFYQ96Z
S3_BUCKET ?= zte-testcase-run-zteapne2
FRONTEND_DIR = frontend
FRONTEND_BUILD_DIR = $(FRONTEND_DIR)/dist

.PHONY: frontend-build
frontend-build: ## 프론트엔드 빌드
	@echo "🔨 프론트엔드를 빌드합니다..."
	@cd $(FRONTEND_DIR) && npm install
	@cd $(FRONTEND_DIR) && npm run build
	@echo "✅ 프론트엔드 빌드 완료: $(FRONTEND_BUILD_DIR)"

.PHONY: s3-upload
s3-upload: check-aws ## S3에 빌드 파일 업로드
	@echo "📤 S3에 파일을 업로드합니다..."
	@if [ ! -d "$(FRONTEND_BUILD_DIR)" ]; then \
		echo "❌ Error: 빌드 디렉토리가 없습니다: $(FRONTEND_BUILD_DIR)"; \
		echo "💡 먼저 빌드를 실행하세요: make frontend-build"; \
		exit 1; \
	fi
	@echo "Bucket: s3://$(S3_BUCKET)/"
	@aws s3 sync $(FRONTEND_BUILD_DIR)/ s3://$(S3_BUCKET)/ \
		--delete \
		--cache-control "public, max-age=31536000" \
		--exclude "index.html" \
		--exclude "*.map"
	@aws s3 cp $(FRONTEND_BUILD_DIR)/index.html s3://$(S3_BUCKET)/index.html \
		--cache-control "public, max-age=0, must-revalidate" \
		--content-type "text/html"
	@echo "✅ S3 업로드 완료"

.PHONY: cf-invalidate
cf-invalidate: check-aws ## CloudFront 캐시 무효화
	@echo "🔄 CloudFront 캐시를 무효화합니다..."
	@echo "Distribution ID: $(CLOUDFRONT_ID)"
	@INVALIDATION_ID=$$(aws cloudfront create-invalidation \
		--distribution-id $(CLOUDFRONT_ID) \
		--paths "/*" \
		--query 'Invalidation.Id' \
		--output text); \
	echo "✅ 무효화 시작됨: $$INVALIDATION_ID"; \
	echo ""; \
	echo "📊 무효화 상태를 확인하려면:"; \
	echo "  aws cloudfront get-invalidation --distribution-id $(CLOUDFRONT_ID) --id $$INVALIDATION_ID"

.PHONY: cf-status
cf-status: check-aws ## CloudFront 배포 상태 확인
	@echo "📊 CloudFront 배포 상태:"
	@aws cloudfront get-distribution --id $(CLOUDFRONT_ID) \
		--query 'Distribution.{Status:Status,DomainName:DomainName,Enabled:DistributionConfig.Enabled}' \
		--output table

.PHONY: frontend-deploy
frontend-deploy: check-aws frontend-build s3-upload cf-invalidate ## 전체 프론트엔드 배포 프로세스
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "✅ 프론트엔드 배포 완료!"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@DOMAIN=$$(aws cloudfront get-distribution --id $(CLOUDFRONT_ID) \
		--query 'Distribution.DomainName' --output text); \
	echo "🌐 CloudFront URL: https://$$DOMAIN"; \
	echo "📦 S3 Bucket: s3://$(S3_BUCKET)"; \
	echo ""; \
	echo "💡 캐시 무효화는 2-5분 정도 소요됩니다."
