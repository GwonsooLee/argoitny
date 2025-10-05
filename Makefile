.PHONY: help up down restart logs logs-backend logs-frontend logs-mysql ps clean build stop start

# Default target
help:
	@echo "AlgoItny - 사용 가능한 명령어:"
	@echo ""
	@echo "  make up           - 모든 서비스 시작 (백그라운드)"
	@echo "  make down         - 모든 서비스 중지 및 제거"
	@echo "  make restart      - 모든 서비스 재시작"
	@echo "  make stop         - 모든 서비스 중지 (제거하지 않음)"
	@echo "  make start        - 중지된 서비스 다시 시작"
	@echo "  make build        - 이미지 다시 빌드 후 시작"
	@echo ""
	@echo "  make logs         - 모든 서비스 로그 보기 (실시간)"
	@echo "  make logs-backend - 백엔드 로그만 보기"
	@echo "  make logs-frontend- 프론트엔드 로그만 보기"
	@echo "  make logs-mysql   - MySQL 로그만 보기"
	@echo ""
	@echo "  make ps           - 실행 중인 컨테이너 상태 확인"
	@echo "  make clean        - 모든 컨테이너, 볼륨, 이미지 제거 (주의!)"
	@echo ""
	@echo "  make shell-backend - 백엔드 컨테이너 쉘 접속"
	@echo "  make shell-frontend- 프론트엔드 컨테이너 쉘 접속"
	@echo "  make shell-mysql  - MySQL 컨테이너 쉘 접속"
	@echo ""
	@echo "  make migrate      - Django 마이그레이션 실행"
	@echo "  make makemigrations- Django 마이그레이션 파일 생성"

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
	@echo "🔄 모든 서비스를 재시작합니다..."
	docker-compose restart
	@echo "✅ 서비스가 재시작되었습니다!"

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
	docker-compose exec backend python manage.py test

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
