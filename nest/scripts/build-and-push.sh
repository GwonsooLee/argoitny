#!/bin/bash

# Build and push Docker image to ECR
# Usage: ./build-and-push.sh [version]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-ap-northeast-2}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
ECR_REPOSITORY=${ECR_REPOSITORY:-algoitny-backend}
VERSION=${1:-latest}

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_NAME="${ECR_REGISTRY}/${ECR_REPOSITORY}"

echo -e "${GREEN}Building and pushing AlgoItny Backend to ECR${NC}"
echo "Registry: ${ECR_REGISTRY}"
echo "Repository: ${ECR_REPOSITORY}"
echo "Version: ${VERSION}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}Checking ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} > /dev/null 2>&1 || \
    aws ecr create-repository \
        --repository-name ${ECR_REPOSITORY} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
cd ../backend
docker build -t ${ECR_REPOSITORY}:${VERSION} .

# Tag image
echo -e "${YELLOW}Tagging image...${NC}"
docker tag ${ECR_REPOSITORY}:${VERSION} ${IMAGE_NAME}:${VERSION}
docker tag ${ECR_REPOSITORY}:${VERSION} ${IMAGE_NAME}:latest

# Push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker push ${IMAGE_NAME}:${VERSION}
docker push ${IMAGE_NAME}:latest

# Get image digest
IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name ${ECR_REPOSITORY} \
    --image-ids imageTag=${VERSION} \
    --region ${AWS_REGION} \
    --query 'imageDetails[0].imageDigest' \
    --output text)

echo ""
echo -e "${GREEN}✓ Successfully built and pushed image${NC}"
echo "Image: ${IMAGE_NAME}:${VERSION}"
echo "Digest: ${IMAGE_DIGEST}"
echo ""
echo "To deploy this image to EKS:"
echo "  helm upgrade --install algoitny-backend ../nest \\"
echo "    --set image.tag=${VERSION} \\"
echo "    --values ../nest/values-production.yaml"
