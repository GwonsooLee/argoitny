# LLM Service Configuration Guide

AlgoItny는 Gemini와 OpenAI를 모두 지원합니다. 이 가이드는 설정 방법과 사용법을 설명합니다.

## 목차
1. [빠른 시작](#빠른-시작)
2. [설정 방법](#설정-방법)
3. [환경 변수](#환경-변수)
4. [사용법](#사용법)
5. [비용 비교](#비용-비교)

---

## 빠른 시작

### Gemini 사용 (기본값, 권장)

```bash
# .env 파일 또는 환경 변수
GEMINI_API_KEY=your-gemini-api-key
DEFAULT_LLM_SERVICE=gemini
```

### OpenAI 사용

```bash
# .env 파일 또는 환경 변수
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-5  # 또는 gpt-5-mini, gpt-5-nano, gpt-5-codex
DEFAULT_LLM_SERVICE=openai
```

### 두 가지 모두 사용 (하이브리드)

```bash
# 두 API 키 모두 설정
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=sk-your-openai-api-key

# 기본값은 Gemini (비용 절감)
DEFAULT_LLM_SERVICE=gemini

# 필요시 코드에서 OpenAI로 전환 가능
```

---

## 설정 방법

### 1. API 키 발급

#### Gemini API Key
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 방문
2. "Get API Key" 클릭
3. API 키 복사

**무료 할당량**:
- 분당 15 requests
- 일일 1,500 requests
- 월간 $0 (무료)

#### OpenAI API Key
1. [OpenAI Platform](https://platform.openai.com/api-keys) 방문
2. "Create new secret key" 클릭
3. API 키 복사

**가격**:
- GPT-5: Input $1.25/M tokens, Output $10/M tokens
- GPT-5-mini: Input $0.25/M tokens, Output $2/M tokens
- GPT-5-nano: Input $0.05/M tokens, Output $0.40/M tokens
- Cached input: $0.125/M tokens (90% 할인)

### 2. Secrets Manager 설정 (프로덕션)

#### AWS Secrets Manager
```bash
# Gemini API Key 저장
aws secretsmanager create-secret \
    --name algoitny/production/gemini-api-key \
    --secret-string "your-gemini-api-key"

# OpenAI API Key 저장
aws secretsmanager create-secret \
    --name algoitny/production/openai-api-key \
    --secret-string "sk-your-openai-api-key"
```

#### 환경 변수 (개발)
```bash
# .env 파일
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-5-mini  # 또는 gpt-5, gpt-5-nano, gpt-5-codex
DEFAULT_LLM_SERVICE=gemini
```

### 3. Config 파일 설정 (선택사항)

```yaml
# config/config.yaml
openai:
  model: gpt-5-mini  # 기본 모델 (gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-codex)
  finetuned_model: ""  # Fine-tuned 모델 (있는 경우, GPT-5는 fine-tuning 미지원)

llm:
  default_service: gemini  # 'gemini' 또는 'openai'
```

---

## 환경 변수

### 필수 변수

| 변수 | 설명 | 예제 |
|------|------|------|
| `GEMINI_API_KEY` | Gemini API 키 (Gemini 사용시) | `AIza...` |
| `OPENAI_API_KEY` | OpenAI API 키 (OpenAI 사용시) | `sk-proj-...` |

### 선택 변수

| 변수 | 기본값 | 설명 |
|------|-------|------|
| `DEFAULT_LLM_SERVICE` | `gemini` | 기본 LLM 서비스 (`gemini` 또는 `openai`) |
| `OPENAI_MODEL` | `gpt-5` | OpenAI 모델 (`gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-codex`) |
| `OPENAI_FINETUNED_MODEL` | ` ` | Fine-tuned 모델 ID (GPT-5-mini/nano만 지원) |

---

## 사용법

### 1. 기본 사용 (설정된 기본 서비스 사용)

```python
from api.services.llm_factory import LLMServiceFactory

# 설정된 기본 LLM 서비스 사용 (DEFAULT_LLM_SERVICE)
llm_service = LLMServiceFactory.create_service()

# 문제 메타데이터 추출
metadata = llm_service.extract_problem_metadata_from_url("https://codeforces.com/problemset/problem/1234/A")

# 솔루션 생성
solution = llm_service.generate_solution_for_problem(metadata)
```

### 2. 특정 서비스 지정

```python
# Gemini 강제 사용
gemini_service = LLMServiceFactory.create_service('gemini')

# OpenAI 강제 사용
openai_service = LLMServiceFactory.create_service('openai')
```

### 3. 사용 가능한 서비스 확인

```python
from api.services.llm_factory import LLMServiceFactory

# 설정된 API 키 기반으로 사용 가능한 서비스 확인
available = LLMServiceFactory.get_available_services()
print(f"Available services: {available}")  # ['gemini', 'openai'] 또는 ['gemini'] 등

# 현재 기본 서비스 확인
default = LLMServiceFactory.get_default_service()
print(f"Default service: {default}")  # 'gemini' 또는 'openai'
```

### 4. Tasks에서 사용

```python
# api/tasks.py에서 자동으로 기본 서비스 사용
@shared_task
def extract_problem_info_task(self, problem_url, job_id=None):
    # DEFAULT_LLM_SERVICE 설정에 따라 Gemini 또는 OpenAI 사용
    llm_service = LLMServiceFactory.create_service()

    # 메타데이터 추출
    problem_metadata = llm_service.extract_problem_metadata_from_url(problem_url)

    # 솔루션 생성
    solution = llm_service.generate_solution_for_problem(problem_metadata)
```

### 5. 하이브리드 전략

```python
# 복잡한 문제는 OpenAI, 일반 문제는 Gemini
def get_appropriate_llm(difficulty_rating):
    if difficulty_rating and difficulty_rating >= 2500:
        # 어려운 문제: OpenAI 사용 (더 정확)
        return LLMServiceFactory.create_service('openai')
    else:
        # 일반 문제: Gemini 사용 (무료/저렴)
        return LLMServiceFactory.create_service('gemini')

# 사용 예제
llm_service = get_appropriate_llm(problem_difficulty)
solution = llm_service.generate_solution_for_problem(metadata)
```

---

## 비용 비교

### Gemini (기본 권장)

**무료 할당량** (2024년 기준):
- 분당 15 requests
- 일일 1,500 requests
- **비용: $0/월**

**유료** (필요시):
- Gemini 1.5 Pro: Input $1.25/M tokens, Output $5/M tokens
- Gemini 1.5 Flash: Input $0.075/M tokens, Output $0.30/M tokens

### OpenAI

**GPT-5** (최고 성능, 통합 모델):
- Input: $1.25/M tokens
- Output: $10.00/M tokens
- Cached input: $0.125/M tokens (90% 할인)

**GPT-5-mini** (권장, 가성비 우수):
- Input: $0.25/M tokens
- Output: $2.00/M tokens

**GPT-5-nano** (가장 저렴):
- Input: $0.05/M tokens
- Output: $0.40/M tokens

**GPT-5-codex** (코딩 최적화):
- 가격은 GPT-5와 동일, 코딩 작업에 특화

### 비용 예상 (월간 1,000개 문제 처리)

| 시나리오 | LLM | 월간 비용 (추정) |
|----------|-----|-----------------|
| 기본 (Gemini Free) | Gemini 2.5 Pro | **$0** |
| 저비용 (OpenAI Nano) | GPT-5-nano | ~$5-10 |
| 중저비용 (OpenAI Mini) | GPT-5-mini | ~$20-40 |
| 고성능 (OpenAI) | GPT-5 | ~$80-150 |
| 하이브리드 | 80% Gemini + 20% GPT-5-mini | ~$5-15 |

**권장**: **Gemini (무료)** 또는 **하이브리드** 전략

---

## 기능 비교

| 기능 | Gemini | OpenAI | 비고 |
|------|--------|--------|------|
| 문제 메타데이터 추출 | ✅ | ✅ | 동일 |
| 솔루션 생성 | ✅ | ✅ | 동일 |
| 테스트 케이스 생성 | ✅ | ⚠️ | OpenAI는 미구현 (Gemini 사용) |
| 힌트 생성 | ✅ | ⚠️ | OpenAI는 미구현 (Gemini 사용) |
| Fine-tuning | ⚠️ | ✅ | OpenAI만 공식 지원 |
| JSON 모드 | ✅ | ✅ | Structured output |
| 한국어 지원 | ✅✅ | ✅ | Gemini가 우수 |
| 컨텍스트 길이 | 2M tokens | 272K tokens (input) / 128K tokens (output) | Gemini가 훨씬 김 |
| 무료 할당량 | ✅ 큼 | ❌ 없음 | Gemini 유리 |

---

## 추천 시나리오

### 1. 스타트업/개인 프로젝트 (비용 최소화)
```bash
DEFAULT_LLM_SERVICE=gemini
GEMINI_API_KEY=your-key
```
- **비용**: $0/월
- **성능**: 충분히 우수
- **제한**: 일일 1,500 requests (충분함)

### 2. 프로덕션 (성능 우선)
```bash
DEFAULT_LLM_SERVICE=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-5-mini  # 또는 gpt-5-codex (코딩에 최적화)
```
- **비용**: $20-50/월
- **성능**: 매우 우수
- **장점**: Fine-tuning 가능, 일관성 높음, 코딩 작업에 특화

### 3. 하이브리드 (비용 최적화)
```bash
# 두 API 키 모두 설정
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
DEFAULT_LLM_SERVICE=gemini

# 코드에서 전략적 선택
def get_llm(difficulty):
    return 'openai' if difficulty >= 2500 else 'gemini'
```
- **비용**: $3-15/월
- **성능**: 우수
- **장점**: 상황별 최적 모델 사용

---

## 전환 시나리오

### Gemini에서 OpenAI로 전환

```bash
# Before
DEFAULT_LLM_SERVICE=gemini

# After
DEFAULT_LLM_SERVICE=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-5-mini  # 또는 gpt-5-codex (코딩 최적화)
```

서비스 재시작하면 즉시 적용됩니다.

### Fine-tuned 모델 사용

```bash
# OpenAI에서 fine-tuning 완료 후
DEFAULT_LLM_SERVICE=openai
OPENAI_FINETUNED_MODEL=ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx
```

Fine-tuned 모델이 설정되면 자동으로 사용됩니다.
**참고**: GPT-5는 fine-tuning을 지원하지 않습니다. GPT-5-mini 또는 GPT-5-nano를 사용하세요.

---

## 문제 해결

### 1. "API key not configured" 오류

```python
# 확인
from django.conf import settings
print(f"Gemini key exists: {bool(settings.GEMINI_API_KEY)}")
print(f"OpenAI key exists: {bool(settings.OPENAI_API_KEY)}")
```

**해결**:
- `.env` 파일에 API 키 추가
- 또는 환경 변수 설정

### 2. "Invalid LLM service type" 오류

```bash
# DEFAULT_LLM_SERVICE가 올바른지 확인
echo $DEFAULT_LLM_SERVICE  # 'gemini' 또는 'openai'이어야 함
```

**해결**:
- `DEFAULT_LLM_SERVICE=gemini` 또는 `DEFAULT_LLM_SERVICE=openai`로 설정

### 3. OpenAI에서 "Not Implemented" 오류

**원인**: 테스트 케이스 생성이나 힌트 생성은 OpenAI에서 미구현

**해결**:
- 해당 기능은 Gemini 사용
- 또는 OpenAIService에 기능 추가 (기여 환영!)

---

## 다음 단계

1. **[OpenAI Fine-Tuning Guide](./OPENAI_FINETUNING_GUIDE.md)**: OpenAI 모델 fine-tuning 방법
2. **데이터 수집**: Validation passed 문제 100-500개 수집
3. **성능 모니터링**: `validation_passed` rate, `needs_review` rate 추적
4. **비용 최적화**: 하이브리드 전략 구현

---

## 기여

OpenAI 서비스에 누락된 기능 (테스트 케이스 생성, 힌트 생성) 구현을 환영합니다!

```bash
# 기여 방법
1. backend/api/services/openai_service.py 수정
2. GeminiService의 해당 메서드 참고
3. Pull Request 생성
```
