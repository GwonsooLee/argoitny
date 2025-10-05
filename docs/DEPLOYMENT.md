# AlgoItny Backend - Helm 배포 가이드

## 🚀 빠른 배포

```bash
# 1. 릴리스된 버전으로 배포
make deploy VERSION=v1.0.0

# 2. 최신 tag로 자동 배포
make deploy

# 3. 배포 상태 확인
make k8s-status
```

## 📋 배포 명령어

### `make deploy` - EKS에 배포

Helm을 사용하여 EKS 클러스터에 배포합니다.

```bash
# 특정 버전 배포
make deploy VERSION=v1.0.0

# 최신 tag 자동 감지하여 배포
make deploy

# 다른 namespace에 배포
make deploy VERSION=v1.0.0 HELM_NAMESPACE=staging

# 다른 values 파일 사용
make deploy VERSION=v1.0.0 HELM_VALUES_FILE=values-staging.yaml
```

**실행 과정:**

```
🚀 AlgoItny Backend Deployment
════════════════════════════════════════════════════════════════

📦 Deployment Information:
  Cluster Context: arn:aws:eks:ap-northeast-2:123456789012:cluster/algoitny-eks-cluster
  Namespace: default
  Release: algoitny-backend
  Version: v1.0.0
  Chart: nest
  Values: values-production.yaml

위 설정으로 배포하시겠습니까? (y/N) y

🔍 Step 1/3: Helm 차트 검증...
✅ Helm 차트 검증 완료

🚀 Step 2/3: Helm으로 배포 중...
Release "algoitny-backend" does not exist. Installing it now.
NAME: algoitny-backend
...
✅ Helm 배포 완료!

📊 Step 3/3: 배포 상태 확인...

=== Pods ===
NAME                                           READY   STATUS    RESTARTS   AGE
algoitny-backend-gunicorn-5d7b8f9c7d-abc12    1/1     Running   0          1m
algoitny-backend-gunicorn-5d7b8f9c7d-def34    1/1     Running   0          1m
algoitny-backend-celery-worker-7c8d9e6f-ghi56 1/1     Running   0          1m
algoitny-backend-celery-beat-6b9c8d7e-jkl78   1/1     Running   0          1m

=== Services ===
NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
algoitny-backend   ClusterIP   10.100.123.45   <none>        80/TCP    1m

=== Ingress ===
NAME               CLASS   HOSTS              ADDRESS                                    PORTS   AGE
algoitny-backend   alb     api.testcase.run   k8s-default-algoitny-abc123.elb...        80,443  1m

════════════════════════════════════════════════════════════════
✅ 배포 완료!
════════════════════════════════════════════════════════════════

📝 유용한 명령어:
  make k8s-status    - 배포 상태 확인
  make k8s-logs      - 로그 확인
  make k8s-rollback  - 이전 버전으로 롤백
```

## 🔍 배포 전 검증

### Helm Dry-Run

실제 배포 없이 manifest를 미리 확인:

```bash
make helm-dry-run VERSION=v1.0.0
```

### Helm Template

렌더링된 manifest 확인:

```bash
make helm-template VERSION=v1.0.0 > manifests.yaml
```

### Helm Lint

차트 검증:

```bash
make helm-lint
```

### Helm Diff (플러그인 필요)

현재 배포와 새 버전 비교:

```bash
# helm-diff 플러그인 설치
helm plugin install https://github.com/databus23/helm-diff

# 변경사항 비교
make helm-diff VERSION=v1.0.0
```

## 📊 배포 상태 확인

### `make k8s-status` - 전체 상태 확인

```bash
make k8s-status
```

**출력:**
- Pods 목록 및 상태
- Services
- Ingress (ALB)
- HPA 상태
- KEDA ScaledObject 상태

### 개별 리소스 확인

```bash
# Pods만 확인
kubectl get pods -n default -l app.kubernetes.io/name=algoitny-backend

# Services 확인
kubectl get svc -n default

# Ingress 확인
kubectl get ingress -n default

# HPA 확인
kubectl get hpa -n default

# Events 확인
kubectl get events -n default --sort-by='.lastTimestamp'
```

## 📋 로그 확인

### `make k8s-logs` - 인터랙티브 로그 확인

```bash
make k8s-logs
```

컴포넌트 선택:
1. Gunicorn (Django API)
2. Celery Worker
3. Celery Beat
4. All

### 개별 컴포넌트 로그

```bash
# Gunicorn 로그
make k8s-logs-gunicorn

# Celery Worker 로그
make k8s-logs-celery

# Celery Beat 로그
make k8s-logs-beat
```

### 직접 kubectl 사용

```bash
# 특정 Pod 로그
kubectl logs -n default POD_NAME

# 이전 컨테이너 로그 (crash 시)
kubectl logs -n default POD_NAME --previous

# 여러 Pod 동시에
kubectl logs -n default -l app.kubernetes.io/component=gunicorn --tail=100

# 실시간 스트리밍
kubectl logs -n default -l app.kubernetes.io/component=gunicorn -f
```

## 🔄 롤백

### `make k8s-rollback` - 인터랙티브 롤백

```bash
make k8s-rollback
```

**실행 과정:**

```
🔄 롤백할 revision을 확인합니다...

REVISION  UPDATED                   STATUS      CHART                    APP VERSION  DESCRIPTION
1         Mon Oct  6 10:00:00 2025  superseded  algoitny-backend-1.0.0   1.0.0        Install complete
2         Mon Oct  6 11:00:00 2025  superseded  algoitny-backend-1.0.0   1.0.0        Upgrade complete
3         Mon Oct  6 12:00:00 2025  deployed    algoitny-backend-1.0.0   1.0.0        Upgrade complete

롤백할 revision 번호를 입력하세요 (0=이전 버전): 2

Revision 2으로 롤백합니다...
Rollback was a success! Happy Helming!
✅ 롤백 완료
```

### 직접 Helm 사용

```bash
# 이전 버전으로 롤백
helm rollback algoitny-backend -n default

# 특정 revision으로 롤백
helm rollback algoitny-backend 2 -n default

# 히스토리 확인
helm history algoitny-backend -n default
```

## 🗑️ 배포 삭제

### `make k8s-undeploy` - 배포 삭제

```bash
make k8s-undeploy
```

**경고:** 이 작업은 되돌릴 수 없습니다!

```
⚠️  WARNING: algoitny-backend를 삭제합니다!
정말로 삭제하시겠습니까? (yes/N) yes

release "algoitny-backend" uninstalled
✅ 삭제 완료
```

## 🔧 설정 변경

### 환경 변수

```bash
# Namespace 변경
make deploy VERSION=v1.0.0 HELM_NAMESPACE=production

# Release 이름 변경
make deploy VERSION=v1.0.0 HELM_RELEASE_NAME=algoitny-api

# Values 파일 변경
make deploy VERSION=v1.0.0 HELM_VALUES_FILE=values-staging.yaml
```

### values 파일 직접 수정

```bash
# values-production.yaml 수정
vi nest/values-production.yaml

# 변경사항 적용
make deploy VERSION=v1.0.0
```

### Helm set으로 값 오버라이드

```bash
cd nest

helm upgrade --install algoitny-backend . \
  --values values-production.yaml \
  --set image.tag=v1.0.0 \
  --set gunicorn.replicaCount=5 \
  --set celeryWorker.keda.minReplicas=3
```

## 📈 스케일링

### HPA (Horizontal Pod Autoscaler)

Gunicorn은 HPA로 자동 스케일링됩니다:
- CPU 사용률 70% 기준
- Memory 사용률 80% 기준
- Min: 2 replicas, Max: 20 replicas

```bash
# HPA 상태 확인
kubectl get hpa -n default

# HPA 상세 정보
kubectl describe hpa algoitny-backend-gunicorn -n default
```

### KEDA (Kubernetes Event-Driven Autoscaling)

Celery Worker는 Redis 큐 길이 기반으로 스케일링됩니다:
- 큐에 메시지 10개 이상일 때 스케일 업
- Min: 3 replicas, Max: 30 replicas

```bash
# KEDA ScaledObject 확인
kubectl get scaledobject -n default

# ScaledObject 상세 정보
kubectl describe scaledobject algoitny-backend-celery-worker -n default
```

### 수동 스케일링

```bash
# Gunicorn 수동 스케일링 (HPA가 다시 조정함)
kubectl scale deployment algoitny-backend-gunicorn -n default --replicas=5

# 또는 values 수정 후 재배포
make deploy VERSION=v1.0.0
```

## 🐛 트러블슈팅

### Pods가 Running 상태가 아닐 때

```bash
# Pod 상태 확인
kubectl get pods -n default

# Pod 상세 정보
kubectl describe pod POD_NAME -n default

# 로그 확인
kubectl logs POD_NAME -n default

# 이전 컨테이너 로그 (crash 시)
kubectl logs POD_NAME -n default --previous
```

### ImagePullBackOff

```bash
# ECR에 이미지가 있는지 확인
make ecr-list

# ECR 로그인 권한 확인
kubectl describe pod POD_NAME -n default

# Service Account 확인
kubectl get sa algoitny-backend-sa -n default -o yaml
```

### Ingress (ALB)가 생성되지 않을 때

```bash
# Ingress 상태 확인
kubectl describe ingress algoitny-backend -n default

# AWS Load Balancer Controller 로그
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Ingress annotations 확인
kubectl get ingress algoitny-backend -n default -o yaml
```

### CrashLoopBackOff

```bash
# 로그 확인
kubectl logs POD_NAME -n default --previous

# 일반적인 원인:
# 1. Database 연결 실패 - Secrets 확인
# 2. Redis 연결 실패 - Redis endpoint 확인
# 3. Migration 오류 - 수동으로 migration 실행
```

### Secrets 확인

```bash
# Secret 존재 확인
kubectl get secret algoitny-backend-secrets -n default

# Secret 상세 (base64 인코딩됨)
kubectl get secret algoitny-backend-secrets -n default -o yaml

# ExternalSecret 상태 확인
kubectl get externalsecret -n default
kubectl describe externalsecret algoitny-backend-external-secret -n default

# SecretStore 확인
kubectl get secretstore -n default
```

## 💡 유용한 팁

### 빠른 업데이트 배포

```bash
# 이미지만 변경하여 빠른 재배포
cd nest
helm upgrade algoitny-backend . \
  --reuse-values \
  --set image.tag=v1.0.1
```

### 특정 Pod만 재시작

```bash
# Deployment 재시작
kubectl rollout restart deployment/algoitny-backend-gunicorn -n default

# 특정 Pod 삭제 (자동으로 재생성됨)
kubectl delete pod POD_NAME -n default
```

### 리소스 사용량 확인

```bash
# Pod별 리소스 사용량
kubectl top pods -n default

# Node별 리소스 사용량
kubectl top nodes
```

### Shell 접속

```bash
# Pod에 Shell 접속
kubectl exec -it POD_NAME -n default -- /bin/sh

# Django shell
kubectl exec -it POD_NAME -n default -- python manage.py shell
```

## 📚 참고 자료

- [RELEASE.md](RELEASE.md) - 릴리스 가이드
- [nest/README.md](../nest/README.md) - Helm 차트 상세 가이드
- [nest/QUICKSTART.md](../nest/QUICKSTART.md) - 빠른 시작 가이드
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
