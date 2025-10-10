# OpenAI Temperature Error - Quick Fix Guide

**Problem**: OpenAI API returning `400 - temperature does not support 0.0 with this model`

**Root Cause**: Using o1/o3 reasoning models (like `gpt-5`) which don't support custom temperature values

---

## ⚡ IMMEDIATE FIX (5 minutes)

### Option A: Switch to GPT-4o (RECOMMENDED - Simplest)

**File**: `backend/config/settings.py` (Line 341)

```python
# Change this line:
OPENAI_MODEL = config.get('openai.model', env_var='OPENAI_MODEL', default='gpt-5')

# To this:
OPENAI_MODEL = config.get('openai.model', env_var='OPENAI_MODEL', default='gpt-4o')
```

**Then restart**:
```bash
cd /Users/gwonsoolee/algoitny
docker-compose restart backend
```

**Result**: Fixed! GPT-4o supports temperature=0.0 ✅

---

### Option B: Remove Temperature for o1/o3 Models (More Complex)

**File**: `backend/api/services/openai_service.py`

**1. Update `get_optimal_temperature()` (Line 21-44):**
```python
def get_optimal_temperature(self, difficulty_rating):
    """
    Get optimal temperature for solution generation.

    Note: o1/o3 reasoning models do NOT support custom temperature.
    They always use temperature=1.0 internally.
    """
    # Check if using o1/o3 model (they don't support temperature)
    if self.model and (self.model.startswith('o1') or self.model.startswith('o3') or self.model == 'gpt-5'):
        return None  # Don't set temperature for o1/o3 models

    # For other models (GPT-4o, GPT-4, etc.), use 0.0 for deterministic output
    return 0.0
```

**2. Update metadata extraction (Line 298-307):**
```python
temperature = self.get_optimal_temperature(difficulty_rating)

# Build completion parameters
params = {
    "model": self.model,
    "messages": [
        {"role": "system", "content": "You are an expert at extracting structured data from competitive programming problems. Always return valid JSON."},
        {"role": "user", "content": prompt}
    ],
    "response_format": {"type": "json_object"}
}

# Only add temperature if supported by model
if temperature is not None:
    params["temperature"] = temperature
    params["top_p"] = 1.0

completion = self.client.chat.completions.create(**params)
```

**3. Update solution generation (Line 559-578):**
```python
temperature = self.get_optimal_temperature(difficulty_rating)

generation_params = {
    "model": self.model,
    "messages": [
        {"role": "system", "content": "You are an expert competitive programmer. Generate correct, optimized C++ solutions."},
        {"role": "user", "content": prompt}
    ],
}

# Only add temperature if supported
if temperature is not None:
    generation_params["temperature"] = temperature
    generation_params["top_p"] = 1.0

# For OpenAI o1/o3 models, add reasoning effort and verbosity control
if self.model.startswith('o1') or self.model.startswith('o3') or self.model == 'gpt-5':
    generation_params["reasoning"] = {"effort": "high"}
    generation_params["text"] = {"verbosity": "low"}
    logger.info(f"Using o1/o3 model optimizations: reasoning=high, verbosity=low, no temperature")
else:
    logger.info(f"Using temperature={temperature}")

completion = self.client.chat.completions.create(**generation_params)
```

**Then restart**:
```bash
cd /Users/gwonsoolee/algoitny
docker-compose restart backend
```

**Result**: Fixed! o1/o3 models work without temperature parameter ✅

---

## 📊 Model Comparison

| Model | Temperature Support | Speed | Cost (per 1M tokens) | Best For |
|-------|-------------------|-------|---------------------|----------|
| **GPT-4o** | ✅ 0.0 - 2.0 | Fast (2-5s) | $5 in / $15 out | Most problems, determinism needed |
| **o1-preview** | ❌ Only 1.0 | Slow (10-30s) | $15 in / $60 out | Expert problems (2500+) |
| **o1-mini** | ❌ Only 1.0 | Medium (5-10s) | $3 in / $12 out | Hard problems (2000+) |
| **o3-mini** | ❌ Only 1.0 | Medium (5-10s) | $3 in / $12 out | Hard problems (2000+) |

---

## 🎯 Recommendation

**Use GPT-4o as default** (Option A above):
- ✅ Supports temperature=0.0 (fully deterministic)
- ✅ Fast response time
- ✅ Lower cost
- ✅ Excellent for 95%+ of competitive programming problems
- ✅ Simple fix (one line change)

**Reserve o1/o3 models for expert problems** (2500+ difficulty) if needed:
- Better reasoning for very complex problems
- Accept non-deterministic output (temperature=1.0)
- Higher cost but better quality for hardest problems

---

## 🔍 Verify Fix

After applying fix and restarting:

```bash
# Check logs
docker logs -f algoitny-backend

# Should NOT see temperature errors anymore
# Should see: "Using temperature=0.0" for GPT-4o
# Or: "Using o1/o3 model optimizations: no temperature" for o1/o3
```

Test problem registration:
```bash
curl -X POST http://localhost:8000/api/problems/register/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://codeforces.com/problemset/problem/4/A",
    "llm_service": "openai"
  }'
```

Should return success (no temperature error) ✅

---

## 📚 Full Details

See: `/Users/gwonsoolee/algoitny/OPENAI_TEMPERATURE_ERROR_ANALYSIS.md` for complete analysis, testing strategy, and cost comparisons.
