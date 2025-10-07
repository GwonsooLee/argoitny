#!/bin/bash

# Deploy AlgoItny Backend to EKS using Helm
# Usage: ./deploy.sh [environment] [version]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
NAMESPACE=${NAMESPACE:-default}
RELEASE_NAME=${RELEASE_NAME:-algoitny-backend}
CHART_PATH="../"

echo -e "${GREEN}Deploying AlgoItny Backend to EKS${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "Version: ${VERSION}"
echo "Namespace: ${NAMESPACE}"
echo "Release: ${RELEASE_NAME}"
echo ""

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: Helm is not installed${NC}"
    exit 1
fi

# Check if kubectl is configured
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${RED}Error: kubectl is not configured or cluster is not accessible${NC}"
    exit 1
fi

# Get current context
CONTEXT=$(kubectl config current-context)
echo -e "${BLUE}Current context: ${CONTEXT}${NC}"
read -p "Continue with this context? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Select values file based on environment
VALUES_FILE="../values-${ENVIRONMENT}.yaml"
if [ ! -f "${VALUES_FILE}" ]; then
    echo -e "${YELLOW}Warning: ${VALUES_FILE} not found, using default values.yaml${NC}"
    VALUES_FILE="../values.yaml"
fi

# Validate Helm chart
echo -e "${YELLOW}Validating Helm chart...${NC}"
helm lint ${CHART_PATH}

# Dry run first
echo -e "${YELLOW}Running dry-run...${NC}"
helm upgrade --install ${RELEASE_NAME} ${CHART_PATH} \
    --namespace ${NAMESPACE} \
    --create-namespace \
    --values ${VALUES_FILE} \
    --set image.tag=${VERSION} \
    --dry-run \
    --debug

echo ""
read -p "Proceed with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Deploy
echo -e "${YELLOW}Deploying...${NC}"
helm upgrade --install ${RELEASE_NAME} ${CHART_PATH} \
    --namespace ${NAMESPACE} \
    --create-namespace \
    --values ${VALUES_FILE} \
    --set image.tag=${VERSION} \
    --wait \
    --timeout 10m

echo ""
echo -e "${GREEN}✓ Deployment completed${NC}"
echo ""

# Show deployment status
echo -e "${BLUE}Deployment status:${NC}"
kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=algoitny-backend

echo ""
echo -e "${BLUE}Services:${NC}"
kubectl get svc -n ${NAMESPACE} -l app.kubernetes.io/name=algoitny-backend

echo ""
echo -e "${BLUE}Ingress:${NC}"
kubectl get ingress -n ${NAMESPACE} ${RELEASE_NAME}

echo ""
echo -e "${BLUE}HPA:${NC}"
kubectl get hpa -n ${NAMESPACE}

echo ""
echo -e "${BLUE}KEDA ScaledObject:${NC}"
kubectl get scaledobject -n ${NAMESPACE} || echo "No ScaledObjects found"

echo ""
echo -e "${GREEN}Deployment Information:${NC}"
echo "Release: ${RELEASE_NAME}"
echo "Namespace: ${NAMESPACE}"
echo "Version: ${VERSION}"
echo ""
echo "To view logs:"
echo "  kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/component=gunicorn --tail=100"
echo "  kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/component=celery-worker --tail=100"
echo ""
echo "To rollback:"
echo "  helm rollback ${RELEASE_NAME} -n ${NAMESPACE}"
