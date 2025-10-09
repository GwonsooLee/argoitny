#!/bin/bash

#####################################################
# AWS S3 + CloudFront 배포 스크립트
#
# 사용법:
#   ./deploy-to-s3.sh <S3_BUCKET_NAME> [CLOUDFRONT_DISTRIBUTION_ID]
#
# 예시:
#   ./deploy-to-s3.sh algoitny-frontend-prod
#   ./deploy-to-s3.sh algoitny-frontend-prod E1XXXXXXXXXX
#####################################################

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 인수 확인
if [ $# -lt 1 ]; then
    log_error "S3 버킷 이름이 필요합니다."
    echo "사용법: $0 <S3_BUCKET_NAME> [CLOUDFRONT_DISTRIBUTION_ID]"
    echo "예시: $0 algoitny-frontend-prod E1XXXXXXXXXX"
    exit 1
fi

S3_BUCKET=$1
CLOUDFRONT_DIST_ID=${2:-""}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DIST_DIR="$PROJECT_DIR/dist"

log_info "==================================="
log_info "AWS S3 + CloudFront 배포 시작"
log_info "==================================="
log_info "S3 Bucket: $S3_BUCKET"
log_info "CloudFront Distribution ID: ${CLOUDFRONT_DIST_ID:-"N/A"}"
log_info "Project Directory: $PROJECT_DIR"
log_info "==================================="

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI가 설치되어 있지 않습니다."
    log_info "설치 방법: https://aws.amazon.com/cli/"
    exit 1
fi

# AWS 자격 증명 확인
log_info "AWS 자격 증명 확인 중..."
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS 자격 증명이 설정되지 않았습니다."
    log_info "다음 명령어를 실행하세요: aws configure"
    exit 1
fi
log_success "AWS 자격 증명 확인 완료"

# S3 버킷 존재 확인
log_info "S3 버킷 존재 확인 중..."
if ! aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
    log_error "S3 버킷 '$S3_BUCKET'이 존재하지 않거나 접근할 수 없습니다."
    exit 1
fi
log_success "S3 버킷 확인 완료"

# 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR"

# 의존성 설치 확인
if [ ! -d "node_modules" ]; then
    log_warning "node_modules가 없습니다. 의존성을 설치합니다..."
    npm install
fi

# 프로덕션 빌드
log_info "프로덕션 빌드 시작..."
log_info "빌드 명령어: npm run build"

if npm run build; then
    log_success "빌드 완료"
else
    log_error "빌드 실패"
    exit 1
fi

# dist 디렉토리 확인
if [ ! -d "$DIST_DIR" ]; then
    log_error "빌드 디렉토리 '$DIST_DIR'를 찾을 수 없습니다."
    exit 1
fi

# index.html 존재 확인
if [ ! -f "$DIST_DIR/index.html" ]; then
    log_error "index.html을 찾을 수 없습니다."
    exit 1
fi

# S3 업로드
log_info "==================================="
log_info "S3 업로드 시작..."
log_info "==================================="

# 1. 정적 자산 업로드 (장기 캐싱)
log_info "Step 1/3: 정적 자산 업로드 (JS, CSS, 이미지 등)"
aws s3 sync "$DIST_DIR/" "s3://$S3_BUCKET" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html" \
    --exclude "*.txt" \
    --exclude "*.json" \
    --exclude "*.xml"

log_success "정적 자산 업로드 완료"

# 2. HTML 파일 업로드 (캐싱 없음)
log_info "Step 2/3: index.html 업로드 (캐싱 없음)"
aws s3 cp "$DIST_DIR/index.html" "s3://$S3_BUCKET/index.html" \
    --cache-control "public, max-age=0, must-revalidate" \
    --content-type "text/html"

log_success "index.html 업로드 완료"

# 3. 기타 메타데이터 파일 업로드
log_info "Step 3/3: 메타데이터 파일 업로드 (robots.txt, manifest.json 등)"
for file in "$DIST_DIR"/*.{txt,json,xml}; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        aws s3 cp "$file" "s3://$S3_BUCKET/$filename" \
            --cache-control "public, max-age=3600" 2>/dev/null || true
    fi
done

log_success "모든 파일 업로드 완료"

# CloudFront 캐시 무효화
if [ -n "$CLOUDFRONT_DIST_ID" ]; then
    log_info "==================================="
    log_info "CloudFront 캐시 무효화 시작..."
    log_info "==================================="

    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_DIST_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)

    log_success "캐시 무효화 요청 완료 (Invalidation ID: $INVALIDATION_ID)"
    log_info "무효화는 몇 분 정도 소요될 수 있습니다."
else
    log_warning "CloudFront Distribution ID가 제공되지 않았습니다. 캐시 무효화를 건너뜁니다."
    log_info "캐시 무효화를 원하면 다음 명령어를 실행하세요:"
    log_info "aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths '/*'"
fi

# 배포 완료
log_info "==================================="
log_success "배포 완료!"
log_info "==================================="
log_info "S3 Bucket: s3://$S3_BUCKET"
log_info "S3 Website URL: http://$S3_BUCKET.s3-website-$(aws configure get region).amazonaws.com"

if [ -n "$CLOUDFRONT_DIST_ID" ]; then
    # CloudFront URL 가져오기
    CLOUDFRONT_URL=$(aws cloudfront get-distribution \
        --id "$CLOUDFRONT_DIST_ID" \
        --query 'Distribution.DomainName' \
        --output text)
    log_info "CloudFront URL: https://$CLOUDFRONT_URL"
fi

log_info "==================================="
log_success "Happy Coding!"
log_info "==================================="
