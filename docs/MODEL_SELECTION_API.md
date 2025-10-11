# LLM Model Selection API

문제 등록 시 사용할 LLM 모델을 선택할 수 있는 API입니다.

## 🎯 사용 가능한 엔드포인트

### 1. 사용 가능한 모델 목록 조회

```http
GET /api/register/models/
```

**Response:**
```json
{
  "models": [
    {
      "id": "gemini-flash",
      "name": "Gemini 1.5 Flash",
      "provider": "Google",
      "description": "Fast and cost-effective model for simple extraction tasks",
      "tier": "simple",
      "cost": {
        "input": 0.075,
        "output": 0.30,
        "unit": "per 1M tokens",
        "estimated_per_problem": "$0.0005"
      },
      "features": {
        "reasoning_effort": ["low"],
        "max_output_tokens": 4096,
        "speed": "very_fast"
      },
      "recommended_for": [
        "Metadata extraction only",
        "Title and constraints",
        "Cost optimization"
      ],
      "limitations": [
        "Not recommended for solution generation",
        "Limited reasoning capabilities"
      ],
      "available": true,
      "is_default_for_metadata": true
    },
    {
      "id": "gemini-pro",
      "name": "Gemini 2.5 Pro",
      "provider": "Google",
      "tier": "moderate",
      "cost": {
        "input": 1.25,
        "output": 5.00,
        "estimated_per_problem": "$0.03"
      },
      "recommended_for": [
        "Easy to Medium problems (1000-1999 rating)",
        "Standard competitive programming"
      ],
      "available": true
    },
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "OpenAI",
      "tier": "moderate",
      "cost": {
        "input": 2.50,
        "output": 10.00,
        "estimated_per_problem": "$0.06"
      },
      "recommended_for": [
        "Medium problems (1500-2499 rating)",
        "Better code quality than Gemini Pro"
      ],
      "available": true
    },
    {
      "id": "gpt-5",
      "name": "GPT-5",
      "provider": "OpenAI",
      "tier": "complex",
      "cost": {
        "input": 10.00,
        "output": 40.00,
        "estimated_per_problem": "$0.20"
      },
      "features": {
        "reasoning_effort": ["low", "medium", "high"],
        "max_output_tokens": 32768,
        "extended_thinking": true
      },
      "recommended_for": [
        "Hard problems (2000+ rating)",
        "Complex algorithms",
        "Deep reasoning required"
      ],
      "available": true,
      "is_default": true
    }
  ],
  "default_model": "gpt-5",
  "default_metadata_extractor": "gemini-flash",
  "configuration_hints": {
    "easy_problems": {
      "recommended": "gemini-pro",
      "reasoning_effort": "low",
      "max_output_tokens": 8192
    },
    "medium_problems": {
      "recommended": "gpt-4o",
      "reasoning_effort": "medium",
      "max_output_tokens": 16384
    },
    "hard_problems": {
      "recommended": "gpt-5",
      "reasoning_effort": "high",
      "max_output_tokens": 32768
    }
  }
}
```

### 2. 모델 추천 받기

난이도나 태그 기반으로 최적의 모델을 추천받습니다.

```http
POST /api/register/models/recommend/
Content-Type: application/json

{
  "difficulty_rating": 2000,
  "tags": ["dp", "graph"]
}
```

**Response:**
```json
{
  "recommended_model": "gpt-5",
  "reasoning_effort": "high",
  "max_output_tokens": 32768,
  "explanation": "Difficulty rating 2000 (Hard) - Using GPT-5 with high reasoning | Complex algorithm detected in tags",
  "alternatives": [
    {
      "model": "gpt-4o",
      "reasoning_effort": "medium",
      "max_output_tokens": 16384,
      "cost_savings": "70%",
      "note": "Cheaper alternative, still good for most problems"
    }
  ],
  "metadata_extraction_note": "Metadata extraction always uses Gemini Flash (most cost-effective)"
}
```

### 3. 문제 등록 시 모델 선택

기존 `extract-problem-info` API에 `llm_config` 파라미터 사용:

```http
POST /api/register/extract-problem-info/
Content-Type: application/json

{
  "problem_url": "https://codeforces.com/contest/1037/problem/D",
  "samples": [],
  "llm_config": {
    "model": "gpt-5",
    "reasoning_effort": "high",
    "max_output_tokens": 32768
  }
}
```

**Parameters:**

| 필드 | 타입 | 필수 | 설명 | 기본값 |
|------|------|------|------|--------|
| `model` | string | No | 사용할 모델 ID (`gemini-pro`, `gpt-4o`, `gpt-5`) | `gpt-5` |
| `reasoning_effort` | string | No | 추론 노력 수준 (`low`, `medium`, `high`) | `medium` |
| `max_output_tokens` | integer | No | 최대 출력 토큰 수 | `8192` |

**Response:**
```json
{
  "problem_id": "codeforces#1037D",
  "platform": "codeforces",
  "problem_identifier": "1037D",
  "job_id": "abc-123-def",
  "status": "PENDING",
  "message": "Problem draft created and extraction job queued for processing"
}
```

## 📊 모델 비교표

| 모델 | 입력 비용 | 출력 비용 | 문제당 예상 비용 | 추천 난이도 | 속도 |
|------|-----------|-----------|------------------|-------------|------|
| **Gemini Flash** | $0.075/1M | $0.30/1M | $0.0005 | 메타데이터만 | ⚡⚡⚡ |
| **Gemini Pro** | $1.25/1M | $5.00/1M | $0.03 | 1000-1999 | ⚡⚡ |
| **GPT-4o** | $2.50/1M | $10.00/1M | $0.06 | 1500-2499 | ⚡⚡ |
| **GPT-5** | $10.00/1M | $40.00/1M | $0.20 | 2000+ | ⚡ |

## 💡 사용 팁

### 1. 자동 메타데이터 추출 (항상 Gemini Flash 사용)
```javascript
// 메타데이터 추출은 항상 Gemini Flash를 자동으로 사용 (94% 저렴)
// 사용자가 선택한 모델은 솔루션 생성에만 적용됩니다
```

### 2. 난이도별 권장 설정

**Easy Problems (< 1500):**
```json
{
  "model": "gemini-pro",
  "reasoning_effort": "low",
  "max_output_tokens": 8192
}
```

**Medium Problems (1500-1999):**
```json
{
  "model": "gpt-4o",
  "reasoning_effort": "medium",
  "max_output_tokens": 16384
}
```

**Hard Problems (2000-2499):**
```json
{
  "model": "gpt-5",
  "reasoning_effort": "medium",
  "max_output_tokens": 16384
}
```

**Very Hard Problems (2500+):**
```json
{
  "model": "gpt-5",
  "reasoning_effort": "high",
  "max_output_tokens": 32768
}
```

### 3. 비용 최적화

1. **메타데이터만 필요한 경우**: 시스템이 자동으로 Gemini Flash 사용
2. **쉬운 문제**: Gemini Pro 사용 (GPT-5 대비 85% 절약)
3. **중간 난이도**: GPT-4o 사용 (GPT-5 대비 70% 절약)
4. **어려운 문제만**: GPT-5 사용

### 4. Reasoning Effort 설정

- **`low`**: 빠르고 저렴, 간단한 문제에 적합
- **`medium`**: 균형잡힌 선택, 대부분의 문제에 적합 (기본값)
- **`high`**: 복잡한 알고리즘 문제에 최적, 더 느리고 비쌈

`high` 설정 시 자동으로 `max_output_tokens`이 128000으로 증가합니다.

## 🔧 프론트엔드 통합 예시

```javascript
// 1. 모델 목록 가져오기
const modelsResponse = await fetch('/api/register/models/');
const { models } = await modelsResponse.json();

// 2. 사용자에게 선택 옵션 표시
const modelSelect = document.getElementById('model-select');
models.forEach(model => {
  const option = document.createElement('option');
  option.value = model.id;
  option.text = `${model.name} - ${model.cost.estimated_per_problem}`;
  option.selected = model.is_default;
  modelSelect.appendChild(option);
});

// 3. 선택된 모델로 문제 등록
const selectedModel = models.find(m => m.id === modelSelect.value);
const llmConfig = {
  model: selectedModel.id,
  reasoning_effort: selectedModel.id === 'gpt-5' ? 'high' : 'medium',
  max_output_tokens: selectedModel.features.max_output_tokens
};

const response = await fetch('/api/register/extract-problem-info/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    problem_url: problemUrl,
    llm_config: llmConfig
  })
});
```

## ⚙️ 백엔드 동작 방식

1. **메타데이터 추출** (항상 Gemini Flash)
   - Title, constraints, samples 추출
   - 가장 저렴한 모델 자동 사용
   - 사용자 선택과 무관

2. **솔루션 생성** (사용자가 선택한 모델)
   - 사용자가 선택한 `llm_config` 사용
   - 난이도에 따라 적절한 모델 선택 가능
   - Retry 로직 포함

## 📈 예상 비용 절감

현재 설정 (모든 작업에 GPT-5):
- 메타데이터: $6.25/월 (1000문제)
- 솔루션: $200/월
- **총합: ~$206/월**

최적화 후:
- 메타데이터 (Flash): $0.50/월 (94% 절감)
- 솔루션 (난이도별):
  - Easy (Gemini Pro): $12/월
  - Medium (GPT-4o): $28/월
  - Hard (GPT-5): $15/월
- **총합: ~$56/월 (73% 절감)**

## 🚨 주의사항

1. **API 키 필요**: 각 모델의 API 키가 설정되어 있어야 사용 가능
2. **High Reasoning**: `reasoning_effort: 'high'`는 GPT-5에서만 사용 가능
3. **토큰 제한**: 각 모델마다 `max_output_tokens` 제한이 다름
4. **자동 조정**: High reasoning 선택 시 자동으로 토큰 수 증가

## 📞 지원

문제가 있거나 질문이 있으시면:
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- 로그 확인: `docker logs algoitny-backend`
