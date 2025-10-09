# OpenAI Fine-Tuning Guide for Competitive Programming

이 가이드는 AlgoItny 프로젝트에서 OpenAI 모델을 fine-tuning하여 competitive programming 문제 해결 성능을 향상시키는 방법을 설명합니다.

## 목차
1. [Fine-Tuning 개요](#fine-tuning-개요)
2. [사용 가능한 모델](#사용-가능한-모델)
3. [데이터 준비](#데이터-준비)
4. [Fine-Tuning 실행](#fine-tuning-실행)
5. [모델 평가 및 배포](#모델-평가-및-배포)
6. [Gemini와의 비교](#gemini와의-비교)

---

## Fine-Tuning 개요

### 왜 Fine-Tuning이 필요한가?

1. **도메인 특화**: Competitive programming은 특수한 도메인이며, fine-tuning을 통해 알고리즘 선택, 최적화 패턴, 엣지 케이스 처리를 개선할 수 있습니다.

2. **일관성 향상**: Base 모델은 때때로 불일치한 결과를 생성하지만, fine-tuning을 통해 일관된 코드 품질을 보장할 수 있습니다.

3. **비용 절감**: Fine-tuned 모델은 더 작고 빠른 모델(예: GPT-5-mini, GPT-5-nano)에서도 base GPT-5와 유사한 성능을 낼 수 있어 비용을 절감할 수 있습니다.

4. **한국어 문제 처리**: Baekjoon과 같은 한국어 문제에 대한 성능을 개선할 수 있습니다.

### Fine-Tuning vs Prompting

| 방법 | 장점 | 단점 | 사용 시점 |
|------|------|------|----------|
| **Prompting** | - 즉시 사용 가능<br>- 데이터 불필요<br>- 설정 간단 | - 토큰 비용 높음<br>- 일관성 낮음<br>- 응답 시간 느림 | 초기 프로토타입, 다양한 작업 |
| **Fine-Tuning** | - 일관성 높음<br>- 응답 빠름<br>- 비용 효율적<br>- 작은 모델 사용 가능 | - 훈련 데이터 필요<br>- 훈련 시간 소요<br>- 초기 비용 발생 | 특정 도메인, 반복 작업, 프로덕션 |

---

## 사용 가능한 모델

**중요**: GPT-5는 fine-tuning을 지원하지 않습니다. Fine-tuning은 GPT-5-mini와 GPT-5-nano에서만 가능합니다.

OpenAI에서 fine-tuning을 지원하는 모델:

### 1. GPT-5-mini (권장)
- **장점**: 빠르고 저렴, GPT-5와 유사한 성능
- **가격**: Training $3.00/M tokens, Input $0.30/M tokens, Output $2.4/M tokens
- **사용 사례**: Competitive programming에 최적 (빠른 응답 + 고품질)

### 2. GPT-5-nano
- **장점**: 가장 저렴, 빠른 추론
- **가격**: Training $1.50/M tokens, Input $0.06/M tokens, Output $0.48/M tokens
- **사용 사례**: 예산이 제한적인 경우, 대량 처리

### 3. GPT-4o-mini (레거시)
- **장점**: 검증된 성능, 안정적
- **가격**: Training $3.00/M tokens, Input $0.3/M tokens, Output $1.2/M tokens
- **사용 사례**: GPT-5-mini로 마이그레이션 전까지 사용

**권장**: **GPT-5-mini**가 가격 대비 성능이 가장 우수합니다. GPT-5는 fine-tuning을 지원하지 않습니다.

---

## 데이터 준비

### 1. 훈련 데이터 형식

OpenAI는 JSONL (JSON Lines) 형식을 사용합니다. 각 라인은 하나의 대화 예제입니다.

```jsonl
{"messages": [{"role": "system", "content": "You are an expert competitive programmer."}, {"role": "user", "content": "Problem: ..."}, {"role": "assistant", "content": "```cpp\n...\n```"}]}
{"messages": [{"role": "system", "content": "You are an expert competitive programmer."}, {"role": "user", "content": "Problem: ..."}, {"role": "assistant", "content": "```cpp\n...\n```"}]}
```

### 2. 데이터 수집 전략

#### Option 1: 현재 시스템에서 수집 (추천)
AlgoItny가 운영되면서 쌓인 데이터 활용:

```python
# backend/scripts/prepare_finetuning_data.py
import json
from api.dynamodb.repositories import ProblemRepository

def collect_training_data():
    """Collect successful problem extractions for training"""
    problem_repo = ProblemRepository()

    # Get all completed problems with validation_passed=True
    problems, _ = problem_repo.list_completed_problems(limit=10000)

    training_data = []
    for problem in problems:
        # Only use problems with successful validation
        metadata = problem.get('metadata', {})
        if not metadata.get('validation_passed', False):
            continue

        # Skip if needs_review
        if metadata.get('needs_review', False):
            continue

        # Format as training example
        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert competitive programmer specializing in solving problems from Codeforces, Baekjoon, and ICPC."
                },
                {
                    "role": "user",
                    "content": f"""Problem Title: {problem['title']}

Input Format and Constraints:
{problem['constraints']}

Sample Test Cases:
{format_samples(problem.get('samples', []))}

Generate a correct, optimized C++ solution that passes all test cases."""
                },
                {
                    "role": "assistant",
                    "content": f"```cpp\n{problem['solution_code']}\n```"
                }
            ]
        }

        training_data.append(training_example)

    # Save to JSONL
    with open('training_data.jsonl', 'w', encoding='utf-8') as f:
        for example in training_data:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"Collected {len(training_data)} training examples")
    return training_data

def format_samples(samples):
    """Format samples for training"""
    formatted = []
    for i, sample in enumerate(samples, 1):
        formatted.append(f"Sample {i}:\nInput:\n{sample['input']}\n\nOutput:\n{sample['output']}")
    return "\n\n".join(formatted)

if __name__ == '__main__':
    collect_training_data()
```

#### Option 2: 공개 데이터셋 사용
- **Codeforces**: Codeforces API를 통해 문제 + editorial 수집
- **Baekjoon**: 공개된 문제 + 유저 솔루션 수집 (라이선스 확인 필요)
- **AtCoder**: AtCoder API 활용

### 3. 데이터 품질 기준

훈련 데이터는 다음 기준을 만족해야 합니다:

- ✅ **정확성**: 모든 샘플 테스트를 통과한 솔루션만 포함
- ✅ **다양성**: 다양한 난이도, 알고리즘 유형, 플랫폼 포함
- ✅ **일관성**: 동일한 코드 스타일, 포맷 유지
- ✅ **최적화**: TLE 없이 통과한 솔루션만 포함
- ✅ **최소 개수**: 최소 50-100개 이상 (더 많을수록 좋음)

### 4. 데이터 검증

```bash
# OpenAI CLI를 사용한 데이터 검증
openai tools fine_tunes.prepare_data -f training_data.jsonl
```

이 명령어는:
- 형식 오류 검사
- 토큰 수 계산
- 추천 사항 제공
- 자동으로 수정된 파일 생성 (`training_data_prepared.jsonl`)

---

## Fine-Tuning 실행

### 1. OpenAI API 키 설정

```bash
export OPENAI_API_KEY="sk-..."
```

또는 Python에서:

```python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

### 2. 훈련 파일 업로드

```python
from openai import OpenAI

client = OpenAI()

# Upload training file
training_file = client.files.create(
    file=open("training_data_prepared.jsonl", "rb"),
    purpose="fine-tune"
)

print(f"File uploaded: {training_file.id}")
```

### 3. Fine-Tuning Job 시작

```python
# Create fine-tuning job
fine_tune_job = client.fine_tuning.jobs.create(
    training_file=training_file.id,
    model="gpt-5-mini-2025-08-07",  # 또는 "gpt-5-nano-2025-08-07" (더 저렴)
    # 참고: "gpt-5"는 fine-tuning을 지원하지 않습니다
    hyperparameters={
        "n_epochs": 3,  # 기본값: 3 (1-50 사이 조정 가능)
        "batch_size": "auto",  # 또는 특정 값 (1, 2, 4, 8, 16, 32)
        "learning_rate_multiplier": "auto"  # 또는 특정 값 (0.02 - 2)
    },
    suffix="competitive-programming"  # 모델 이름 suffix
)

print(f"Fine-tuning job created: {fine_tune_job.id}")
```

### 4. 진행 상황 모니터링

```python
# Check job status
import time

job_id = fine_tune_job.id

while True:
    job = client.fine_tuning.jobs.retrieve(job_id)
    print(f"Status: {job.status}")

    if job.status == "succeeded":
        print(f"Fine-tuned model: {job.fine_tuned_model}")
        break
    elif job.status == "failed":
        print(f"Job failed: {job.error}")
        break

    time.sleep(60)  # Check every minute
```

또는 CLI 사용:

```bash
# List all fine-tuning jobs
openai api fine_tuning.jobs.list

# Get specific job status
openai api fine_tuning.jobs.retrieve -i ftjob-xxx

# Stream events
openai api fine_tuning.jobs.follow -i ftjob-xxx
```

### 5. 훈련 결과 확인

```python
# Get fine-tuning events
events = client.fine_tuning.jobs.list_events(fine_tune_job.id, limit=10)
for event in events.data:
    print(event.message)

# Get training metrics
job = client.fine_tuning.jobs.retrieve(fine_tune_job.id)
print(f"Training metrics: {job.trained_tokens} tokens")
```

---

## 모델 평가 및 배포

### 1. 모델 테스트

```python
# Use fine-tuned model
def test_finetuned_model(model_name):
    client = OpenAI()

    test_prompt = """Problem Title: Sum of Two Numbers

Input Format and Constraints:
First line: two integers A and B (1 ≤ A, B ≤ 10^9)

Sample Test Cases:
Sample 1:
Input:
3 5

Output:
8

Generate a correct, optimized C++ solution."""

    response = client.chat.completions.create(
        model=model_name,  # e.g., "ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx"
        messages=[
            {"role": "system", "content": "You are an expert competitive programmer."},
            {"role": "user", "content": test_prompt}
        ],
        temperature=0.3
    )

    print(response.choices[0].message.content)

# Test your fine-tuned model
test_finetuned_model("ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx")
```

### 2. A/B 테스트 설정

```python
# backend/api/services/openai_service.py에 추가

def __init__(self):
    if settings.OPENAI_API_KEY:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Fine-tuned 모델이 설정되어 있으면 사용
        self.model = getattr(
            settings,
            'OPENAI_FINETUNED_MODEL',
            getattr(settings, 'OPENAI_MODEL', 'gpt-5')
        )
    else:
        self.client = None
        self.model = None
```

Settings 업데이트:

```python
# config/settings.py
OPENAI_FINETUNED_MODEL = config.get(
    'openai.finetuned_model',
    env_var='OPENAI_FINETUNED_MODEL',
    default=''  # 비어있으면 base 모델 사용
)
```

환경 변수로 제어:

```bash
# .env 또는 환경 변수
OPENAI_FINETUNED_MODEL=ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx
# 참고: GPT-5는 fine-tuning을 지원하지 않습니다. GPT-5-mini 또는 GPT-5-nano만 가능합니다.
```

### 3. 성능 메트릭 수집

```python
# backend/scripts/evaluate_model.py

def evaluate_model(model_name, test_problems):
    """Evaluate model on test set"""
    results = {
        'correct': 0,
        'compilation_errors': 0,
        'runtime_errors': 0,
        'wrong_answer': 0,
        'total': len(test_problems)
    }

    for problem in test_problems:
        # Generate solution
        solution = generate_solution(model_name, problem)

        # Validate
        passed, error = validate_solution(solution, problem['samples'])

        if passed:
            results['correct'] += 1
        elif 'compilation' in error.lower():
            results['compilation_errors'] += 1
        elif 'runtime' in error.lower():
            results['runtime_errors'] += 1
        else:
            results['wrong_answer'] += 1

    accuracy = results['correct'] / results['total'] * 100
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Breakdown: {results}")

    return results
```

### 4. 프로덕션 배포

1. **환경 변수 업데이트**:
```bash
# Kubernetes ConfigMap 또는 환경 변수
DEFAULT_LLM_SERVICE=openai
OPENAI_FINETUNED_MODEL=ft:gpt-5-mini-2025-08-07:org:competitive-programming:xxx
```

2. **점진적 롤아웃**:
```python
# 10% 트래픽만 fine-tuned 모델로
import random

def get_llm_service():
    if random.random() < 0.1:  # 10%
        return LLMServiceFactory.create_service('openai')  # Fine-tuned
    else:
        return LLMServiceFactory.create_service('gemini')  # 기존
```

3. **모니터링**:
- 정확도 (validation_passed rate)
- 응답 시간
- API 비용
- 사용자 피드백 (needs_review rate)

---

## Gemini와의 비교

### OpenAI Fine-Tuning

**장점**:
- ✅ Fine-tuning 공식 지원 (GPT-5-mini, GPT-5-nano)
- ✅ 명확한 가격 정책
- ✅ 빠른 훈련 (보통 수십 분)
- ✅ 작은 모델에서도 우수한 성능 (GPT-5-mini)
- ✅ JSON 모드 지원 (structured output)
- ⚠️ GPT-5는 fine-tuning 미지원

**단점**:
- ❌ 훈련 비용 발생
- ❌ 모델 관리 필요
- ❌ API 비용 (Gemini보다 비쌈)

### Gemini

**장점**:
- ✅ Free tier 제공 (한도 내 무료)
- ✅ 긴 컨텍스트 (2M tokens)
- ✅ 한국어 처리 우수
- ✅ Few-shot learning 효과적

**단점**:
- ❌ Fine-tuning 미지원 (Gemini API)
- ❌ Vertex AI로 fine-tuning 가능하지만 복잡
- ❌ 일관성이 OpenAI보다 낮을 수 있음

### 권장 전략

1. **초기 단계**: Gemini + Prompting
2. **데이터 수집**: 100-500개 고품질 문제/솔루션 쌓기
3. **Fine-Tuning**: OpenAI GPT-5-mini fine-tune (GPT-5는 fine-tuning 미지원)
4. **하이브리드**:
   - 복잡한 문제 (2500+ rating): Fine-tuned GPT-5-mini
   - 일반 문제: Gemini (비용 절감)

---

## 추가 리소스

### OpenAI 공식 문서
- [Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [Fine-tuning API Reference](https://platform.openai.com/docs/api-reference/fine-tuning)
- [Best Practices](https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset)

### 가격 정보
- [OpenAI Pricing](https://openai.com/api/pricing/)

### 예제 코드
```bash
# 전체 워크플로우 예제
cd backend/scripts
python prepare_finetuning_data.py  # 데이터 준비
python finetune_openai.py          # Fine-tuning 실행
python evaluate_model.py           # 모델 평가
```

---

## 문제 해결 (Troubleshooting)

### 1. 훈련이 너무 느림
- **원인**: 데이터셋이 너무 큼
- **해결**: `n_epochs`를 줄이거나, 데이터를 필터링

### 2. 모델 성능이 낮음
- **원인**: 훈련 데이터 품질 문제 또는 양 부족
- **해결**:
  - 최소 100-500개 이상의 고품질 예제 사용
  - `validation_passed=True`인 데이터만 사용
  - 다양한 난이도와 알고리즘 유형 포함

### 3. 비용이 너무 높음
- **원인**: 과도한 훈련 또는 잘못된 모델 선택
- **해결**:
  - GPT-5-nano 사용 (GPT-5-mini보다 50% 저렴)
  - `n_epochs` 줄이기 (3 → 1 or 2)
  - 데이터 필터링으로 토큰 수 줄이기
  - **참고**: GPT-5는 fine-tuning을 지원하지 않습니다

### 4. Fine-tuned 모델이 base보다 나쁨
- **원인**: Overfitting 또는 데이터 편향
- **해결**:
  - Validation set으로 평가
  - `n_epochs` 줄이기
  - 더 다양한 훈련 데이터 사용

---

## 요약

1. **데이터 준비**: AlgoItny에서 `validation_passed=True`인 문제 100-500개 수집
2. **Fine-Tuning**: GPT-5-mini로 훈련 (비용 효율적, GPT-5는 fine-tuning 미지원)
3. **평가**: Test set으로 accuracy 측정
4. **배포**: 점진적 롤아웃 (10% → 50% → 100%)
5. **모니터링**: Accuracy, cost, latency 추적

**중요**: GPT-5는 fine-tuning을 지원하지 않습니다. GPT-5-mini 또는 GPT-5-nano를 사용하세요.

**시작하기**: 먼저 Gemini로 100개 이상의 고품질 문제를 수집한 후, GPT-5-mini fine-tuning을 고려하세요!
