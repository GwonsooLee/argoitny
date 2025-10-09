# EKS Quick Start Guide

## Prerequisites

1. AWS CLI configured
2. Terraform >= 1.5.7
3. kubectl installed

## Deploy Cluster

```bash
cd terraform/eks/zte-prod/prod_apnortheast2/algoitny

# Initialize
terraform init

# Plan
terraform plan

# Apply (takes 15-20 minutes)
terraform apply
```

## Configure kubectl

```bash
CLUSTER_NAME=$(terraform output -raw cluster_id)
aws eks update-kubeconfig --region ap-northeast-2 --name $CLUSTER_NAME

# Verify
kubectl get svc
```

## Deploy Application

```bash
# Apply ConfigMap
kubectl apply -f backend/k8s/configmap.yaml

# Deploy your app
kubectl apply -f your-deployment.yaml
```

## Cleanup

```bash
terraform destroy
```
