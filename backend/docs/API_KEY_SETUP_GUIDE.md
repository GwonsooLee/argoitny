# API Key 설정 가이드

이 가이드는 Gemini와 OpenAI API 키를 설정하는 방법을 설명합니다.

## 빠른 설정 (개발 환경)

### 1. 환경 변수로 설정 (가장 쉬움) ✅

프로젝트 루트에 `.env` 파일을 생성하고 API 키를 추가합니다:

```bash
# /Users/gwonsoolee/algoitny/backend/.env

# Gemini API Key (무료)
GEMINI_API_KEY=AIzaSy...your-gemini-key...

# OpenAI API Key (유료)
OPENAI_API_KEY=sk-proj-...your-openai-key...

# 기본 LLM 서비스 선택 ('gemini' 또는 'openai')
DEFAULT_LLM_SERVICE=gemini
```

**주의**: `.env` 파일은 절대 Git에 커밋하지 마세요! `.gitignore`에 추가되어 있는지 확인하세요.

---

## API 키 발급 방법

### Gemini API Key 발급

1. **Google AI Studio** 접속: https://aistudio.google.com/app/apikey
2. "Create API Key" 클릭
3. API 키 복사 (예: `AIzaSyB...`)

**무료 할당량**:
- 분당 15 requests
- 일일 1,500 requests
- **비용: $0/월** ✨

### OpenAI API Key 발급

1. **OpenAI Platform** 접속: https://platform.openai.com/api-keys
2. 로그인 (계정 없으면 생성)
3. "+ Create new secret key" 클릭
4. 이름 입력 후 "Create secret key" 클릭
5. API 키 복사 (예: `sk-proj-...`) - **⚠️ 단 한 번만 표시됨!**

**가격** (GPT-5 기준):
- **GPT-5 (Standard)**: Input $1.25/M tokens, Output $10/M tokens
- **GPT-5-mini**: Input $0.25/M tokens, Output $2/M tokens (60% GPT-5보다 저렴)
- **GPT-5-nano**: Input $0.05/M tokens, Output $0.40/M tokens (가장 저렴)
- **Cached input**: $0.125/M tokens (90% 할인)

---

## 상세 설정 방법

### Option 1: 환경 변수 (권장, 개발용)

#### macOS/Linux:

```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export GEMINI_API_KEY="AIzaSy..."
export OPENAI_API_KEY="sk-proj-..."
export DEFAULT_LLM_SERVICE="gemini"

# 적용
source ~/.bashrc  # 또는 source ~/.zshrc
```

#### Windows:

```cmd
# 시스템 환경 변수 설정
setx GEMINI_API_KEY "AIzaSy..."
setx OPENAI_API_KEY "sk-proj-..."
setx DEFAULT_LLM_SERVICE "gemini"

# 또는 .env 파일 사용 (권장)
```

#### Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEFAULT_LLM_SERVICE=gemini
```

### Option 2: AWS Secrets Manager (프로덕션용)

```bash
# Gemini API Key 저장
aws secretsmanager create-secret \
    --name algoitny/production/GEMINI_API_KEY \
    --secret-string "AIzaSy..."

# OpenAI API Key 저장
aws secretsmanager create-secret \
    --name algoitny/production/OPENAI_API_KEY \
    --secret-string "sk-proj-..."
```

### Option 3: Kubernetes Secrets (프로덕션용)

```bash
# Secret 생성
kubectl create secret generic llm-api-keys \
  --from-literal=GEMINI_API_KEY='AIzaSy...' \
  --from-literal=OPENAI_API_KEY='sk-proj-...' \
  -n algoitny

# Deployment에서 사용
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: algoitny-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: GEMINI_API_KEY
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-api-keys
              key: OPENAI_API_KEY
```

---

## 설정 확인

### 1. Python Shell에서 확인

```bash
cd /Users/gwonsoolee/algoitny/backend
python manage.py shell
```

```python
from django.conf import settings

# API 키가 설정되었는지 확인
print(f"Gemini API Key: {'✓ 설정됨' if settings.GEMINI_API_KEY else '✗ 없음'}")
print(f"OpenAI API Key: {'✓ 설정됨' if settings.OPENAI_API_KEY else '✗ 없음'}")
print(f"Default LLM Service: {settings.DEFAULT_LLM_SERVICE}")

# LLM Factory로 사용 가능 여부 확인
from api.services.llm_factory import LLMServiceFactory

available = LLMServiceFactory.get_available_services()
print(f"사용 가능한 LLM 서비스: {available}")

# 기본 서비스로 LLM 생성 테스트
try:
    llm = LLMServiceFactory.create_service()
    print(f"✓ {settings.DEFAULT_LLM_SERVICE} 서비스 생성 성공!")
except Exception as e:
    print(f"✗ 오류: {e}")
```

### 2. 간단한 테스트

```python
# Gemini 테스트
from api.services.llm_factory import LLMServiceFactory

gemini = LLMServiceFactory.create_service('gemini')
print("Gemini 모델:", gemini.model)  # gemini-2.5-pro

# OpenAI 테스트
openai_svc = LLMServiceFactory.create_service('openai')
print("OpenAI 모델:", openai_svc.model)  # gpt-4o
```

---

## 문제 해결

### 오류: "API key not configured"

```python
# 확인
import os
print(os.environ.get('GEMINI_API_KEY'))
print(os.environ.get('OPENAI_API_KEY'))
```

**해결**:
1. `.env` 파일이 올바른 위치에 있는지 확인
2. 환경 변수가 제대로 로드되는지 확인
3. Django 서버를 재시작

### 오류: "Invalid API key"

**Gemini**:
- API 키가 `AIza`로 시작하는지 확인
- Google AI Studio에서 키가 활성화되어 있는지 확인

**OpenAI**:
- API 키가 `sk-`로 시작하는지 확인
- OpenAI 계정에 크레딧이 있는지 확인
- API 키가 만료되지 않았는지 확인

### 오류: "Invalid LLM service type"

```bash
# DEFAULT_LLM_SERVICE가 올바른지 확인
echo $DEFAULT_LLM_SERVICE  # 'gemini' 또는 'openai'이어야 함
```

---

## 보안 Best Practices

### ✅ 해야 할 것

1. **절대로 Git에 커밋하지 않기**
   ```bash
   # .gitignore에 추가
   .env
   *.env
   secrets.py
   ```

2. **환경 변수 사용**
   - 개발: `.env` 파일
   - 프로덕션: AWS Secrets Manager 또는 Kubernetes Secrets

3. **API 키 로테이션**
   - 정기적으로 API 키 교체 (예: 3개월마다)

4. **최소 권한 원칙**
   - API 키에 필요한 최소한의 권한만 부여

### ❌ 하지 말아야 할 것

1. API 키를 코드에 하드코딩
2. API 키를 Git에 커밋
3. API 키를 로그에 출력
4. API 키를 슬랙/이메일로 전송

---

## 현재 설정 (확인용)

### Gemini
- 모델: **gemini-2.5-pro** ✨ (최신 Pro 모델)
- 위치: `backend/api/services/gemini_service.py:190`
- 무료 할당량 제공

### OpenAI
- 모델: **gpt-5** ✨ (최신 통합 모델, 2025년 8월 출시)
  - 추론 능력과 빠른 응답을 결합한 unified 모델
  - GPT-4o보다 50% 저렴하면서 성능 대폭 향상
- 대체 모델: **gpt-5-mini** (더 저렴), **gpt-5-nano** (가장 저렴), **gpt-5-codex** (코딩 최적화)
- 위치: `backend/config/settings.py:337`
- 유료 (사용량 기반)

---

## 추가 설정 옵션

### OpenAI 모델 변경 (비용 절감)

GPT-5 대신 더 저렴한 모델 사용:

```bash
# .env 파일
OPENAI_MODEL=gpt-5-mini  # GPT-5보다 80% 저렴, 성능은 90% 수준
```

또는

```bash
OPENAI_MODEL=gpt-5-nano  # 가장 저렴, 기본적인 작업에 충분
```

또는 코딩에 최적화된 모델:

```bash
OPENAI_MODEL=gpt-5-codex  # 코딩 작업에 최적화 (경쟁 프로그래밍에 추천)
```

### Fine-tuned 모델 사용

```bash
# .env 파일
OPENAI_FINETUNED_MODEL=ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx
```

Fine-tuned 모델이 설정되면 기본 모델 대신 자동으로 사용됩니다.
**참고**: GPT-5는 fine-tuning을 지원하지 않습니다. GPT-5-mini 또는 GPT-5-nano를 사용하세요.

---

## 요약

1. **API 키 발급**:
   - Gemini: https://aistudio.google.com/app/apikey (무료)
   - OpenAI: https://platform.openai.com/api-keys (유료)

2. **설정 파일 생성** (`/Users/gwonsoolee/algoitny/backend/.env`):
   ```bash
   GEMINI_API_KEY=AIzaSy...
   OPENAI_API_KEY=sk-proj-...
   DEFAULT_LLM_SERVICE=gemini
   ```

3. **서버 재시작**:
   ```bash
   cd /Users/gwonsoolee/algoitny/backend
   python manage.py runserver
   ```

4. **설정 확인**:
   ```bash
   python manage.py shell
   >>> from api.services.llm_factory import LLMServiceFactory
   >>> print(LLMServiceFactory.get_available_services())
   ['gemini', 'openai']
   ```

이제 시작할 준비가 되었습니다! 🚀

---

## 참고 문서

- [LLM Service Configuration Guide](./LLM_SERVICE_CONFIGURATION.md)
- [OpenAI Fine-Tuning Guide](./OPENAI_FINETUNING_GUIDE.md)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)
