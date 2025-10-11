# LLM Optimization Strategy: Multi-Tier Model Selection

## Executive Summary

This document provides a comprehensive strategy for optimizing LLM costs and performance in the Algoitny competitive programming platform by implementing tiered model selection based on task complexity.

**Current State:**
- Using Gemini 2.5 Pro and GPT-5 (OpenAI) for all tasks
- No differentiation based on task complexity
- High costs for simple extraction tasks

**Recommended State:**
- 3-tier model selection based on task complexity
- Estimated cost savings: 60-75%
- Maintained or improved quality for complex tasks

---

## Current LLM Task Analysis

### Task Inventory

Based on codebase analysis, the system performs these LLM tasks:

| Task | Current Model | Complexity | Frequency | Token Usage (avg) |
|------|--------------|------------|-----------|-------------------|
| **Extract Problem Metadata** | Gemini 2.5 Pro | LOW | High | 2K-5K input, 500-1K output |
| **Extract Title** | (part of metadata) | VERY LOW | High | Included above |
| **Extract Constraints** | (part of metadata) | LOW | High | Included above |
| **Extract Sample Test Cases** | Gemini 2.5 Pro | MEDIUM | High | Included above |
| **Generate Solution Code** | GPT-5 or Gemini 2.5 Pro | VERY HIGH | High | 3K-8K input, 2K-8K output |
| **Generate Test Case Generator** | Gemini 2.5 Pro | HIGH | Medium | 2K-5K input, 1K-3K output |
| **Generate Hints** | Gemini 2.5 Pro (hardcoded) | MEDIUM | Low | 1K-3K input, 500-1500 output |

### Cost Analysis (Current)

**Gemini 2.5 Pro Pricing:**
- Input: $1.25 / 1M tokens
- Output: $5.00 / 1M tokens

**GPT-5 Pricing (estimated):**
- Input: $10.00 / 1M tokens
- Output: $30.00 / 1M tokens

**Example: 1000 problem extractions/month**
- Metadata extraction: 1000 × (4K input + 750 output) = ~$10/month (Gemini)
- Solution generation: 1000 × (5K input + 5K output) = ~$200/month (GPT-5)
- **Total: ~$210/month**

---

## Recommended 3-Tier Model Strategy

### Tier 1: Simple Extraction (Fast & Cheap)

**Use Cases:**
- Title extraction
- Basic constraint parsing
- URL parsing
- Simple metadata extraction
- Tag extraction

**Recommended Models:**

1. **GPT-4o Mini (OpenAI)** - BEST CHOICE
   - Input: $0.15 / 1M tokens
   - Output: $0.60 / 1M tokens
   - Speed: Very fast (2-3 seconds)
   - Quality: Excellent for structured extraction
   - **Cost vs Gemini: 88% cheaper**

2. **Claude 3.5 Haiku (Anthropic)** - ALTERNATIVE
   - Input: $0.80 / 1M tokens
   - Output: $4.00 / 1M tokens
   - Speed: Very fast
   - Quality: Excellent for text understanding
   - **Cost vs Gemini: 20% cheaper**

3. **Gemini 1.5 Flash (Google)** - CURRENT PROVIDER ALTERNATIVE
   - Input: $0.075 / 1M tokens (up to 128K context)
   - Output: $0.30 / 1M tokens
   - Speed: Very fast
   - Quality: Good for simple tasks
   - **Cost vs Gemini 2.5 Pro: 94% cheaper**

**Recommendation: Use Gemini 1.5 Flash** (same provider, minimal code changes)

### Tier 2: Moderate Complexity (Balanced)

**Use Cases:**
- Sample test case extraction (requires precision)
- Hint generation
- Problem classification/tagging
- Basic code analysis
- Error message interpretation

**Recommended Models:**

1. **Claude 3.5 Sonnet (Anthropic)** - BEST CHOICE
   - Input: $3.00 / 1M tokens
   - Output: $15.00 / 1M tokens
   - Speed: Fast (5-8 seconds)
   - Quality: Excellent reasoning and instruction following
   - Context: 200K tokens
   - **Cost vs GPT-5: 70% cheaper**

2. **Gemini 1.5 Pro (Google)** - ALTERNATIVE
   - Input: $1.25 / 1M tokens
   - Output: $5.00 / 1M tokens
   - Speed: Fast
   - Quality: Very good for analysis
   - Context: 2M tokens
   - **Cost vs GPT-5: 85% cheaper**

3. **GPT-4 Turbo (OpenAI)** - ALTERNATIVE
   - Input: $10.00 / 1M tokens
   - Output: $30.00 / 1M tokens
   - Speed: Medium
   - Quality: Excellent
   - Context: 128K tokens

**Recommendation: Keep Gemini 2.5 Pro** (current model, good balance)

### Tier 3: Complex Reasoning (Premium)

**Use Cases:**
- Solution code generation (especially 2500+ difficulty)
- Test case generator code creation
- Complex algorithm design
- Mathematical proof generation
- Edge case analysis

**Recommended Models:**

1. **GPT-4o with reasoning (OpenAI)** - BEST FOR COMPETITIVE PROGRAMMING
   - Input: $2.50 / 1M tokens (cached: $1.25)
   - Output: $10.00 / 1M tokens (cached: $5.00)
   - Speed: Medium (10-30 seconds)
   - Quality: Excellent for code generation
   - Reasoning: Built-in chain-of-thought
   - **Cost vs GPT-5: 75% cheaper**

2. **Claude 3.5 Sonnet (Anthropic)** - BEST FOR CODE QUALITY
   - Input: $3.00 / 1M tokens (cached: $0.30)
   - Output: $15.00 / 1M tokens (cached: $1.50)
   - Speed: Fast (8-15 seconds)
   - Quality: Excellent for code generation and following complex instructions
   - Context: 200K tokens
   - Caching: 90% discount for repeated prompts
   - **Cost vs GPT-5: 70% cheaper**

3. **Gemini 2.0 Flash Thinking (Google)** - ALTERNATIVE WITH REASONING
   - Input: $0.00 / 1M tokens (free during preview)
   - Output: $0.00 / 1M tokens (free during preview)
   - Speed: Fast (8-20 seconds)
   - Quality: Very good with reasoning
   - Thinking: Built-in reasoning mode
   - **Cost: FREE (during preview), then likely similar to Flash**

**Recommendation: Use GPT-4o for high-difficulty problems (2000+), Claude 3.5 Sonnet for medium (1500-2000), Gemini 2.0 Flash Thinking for easier problems**

---

## Implementation Strategy

### Phase 1: Split Metadata Extraction (Week 1)

**Goal: Reduce metadata extraction costs by 90%**

1. **Create Gemini Flash Service**
   ```python
   # api/services/gemini_flash_service.py
   class GeminiFlashService:
       """Lightweight Gemini Flash for simple extractions"""

       def __init__(self):
           genai.configure(api_key=settings.GEMINI_API_KEY)
           self.model = genai.GenerativeModel('gemini-1.5-flash')

       def extract_simple_metadata(self, webpage_content):
           """Extract title, constraints, basic info only"""
           # Simplified prompt, no sample extraction
           pass

       def extract_samples(self, webpage_content, problem_context):
           """High-precision sample extraction (use Gemini Pro)"""
           # Keep using Gemini 2.5 Pro for samples
           pass
   ```

2. **Update Metadata Extraction Pipeline**
   ```python
   # In tasks.py: extract_problem_info_task

   # STEP 1a: Extract basic metadata with Flash (cheap)
   flash_service = GeminiFlashService()
   basic_metadata = flash_service.extract_simple_metadata(webpage_content)

   # STEP 1b: Extract samples with Pro (accuracy critical)
   pro_service = LLMServiceFactory.create_service('gemini')
   samples = pro_service.extract_samples(webpage_content, basic_metadata)

   # Combine results
   problem_metadata = {**basic_metadata, 'samples': samples}
   ```

**Expected Savings:**
- Metadata cost: $10/month → $1/month (90% reduction)

### Phase 2: Implement Difficulty-Based Solution Generation (Week 2)

**Goal: Use cheaper models for easier problems**

1. **Update LLM Factory**
   ```python
   # api/services/llm_factory.py

   class LLMServiceFactory:
       @staticmethod
       def create_solution_service(difficulty_rating=None):
           """Select model based on difficulty"""
           if difficulty_rating is None or difficulty_rating < 1500:
               # Easy problems: Use Claude 3.5 Sonnet or Gemini Pro
               return LLMServiceFactory.create_service('gemini')

           elif difficulty_rating < 2000:
               # Medium problems: Use Claude 3.5 Sonnet
               return ClaudeSonnetService()

           else:
               # Hard problems (2000+): Use GPT-4o or GPT-5
               return LLMServiceFactory.create_service('openai')
   ```

2. **Add Claude Service**
   ```python
   # api/services/claude_service.py

   from anthropic import Anthropic

   class ClaudeSonnetService:
       """Claude 3.5 Sonnet for balanced cost/performance"""

       def __init__(self):
           self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
           self.model = 'claude-3-5-sonnet-20241022'

       def generate_solution_for_problem(self, problem_metadata, ...):
           """Generate solution with Claude 3.5 Sonnet"""
           # Similar to OpenAI/Gemini implementation
           pass
   ```

3. **Update Solution Generation Call**
   ```python
   # In tasks_solution_generation.py

   def generate_solution_with_retry(problem_metadata, update_progress_callback, llm_config=None):
       # Determine difficulty
       difficulty = problem_metadata.get('difficulty_rating')

       # Select appropriate service
       service = LLMServiceFactory.create_solution_service(difficulty)

       # Generate with selected model
       solution = service.generate_solution_for_problem(problem_metadata, ...)
       return solution
   ```

**Expected Savings:**
- Solution generation: $200/month → $80/month (60% reduction)
- Breakdown:
  - Easy (40%): Gemini Pro at $1.25/$5.00 per 1M
  - Medium (35%): Claude Sonnet at $3.00/$15.00 per 1M
  - Hard (25%): GPT-4o/GPT-5 at $2.50-$10.00 per 1M

### Phase 3: Optimize with Prompt Caching (Week 3)

**Goal: Reduce costs for repeated prompts by 90%**

1. **Implement Claude Prompt Caching**
   ```python
   class ClaudeSonnetService:
       def generate_solution_for_problem(self, problem_metadata, ...):
           # Mark system prompt and few-shot examples for caching
           response = self.client.messages.create(
               model=self.model,
               max_tokens=8192,
               system=[
                   {
                       "type": "text",
                       "text": SYSTEM_PROMPT_WITH_EXAMPLES,  # This gets cached
                       "cache_control": {"type": "ephemeral"}
                   }
               ],
               messages=[
                   {"role": "user", "content": problem_content}  # This is unique
               ]
           )
   ```

2. **Implement OpenAI Prompt Caching**
   ```python
   class OpenAIService:
       def generate_solution_for_problem(self, problem_metadata, ...):
           # Use cached system instructions
           completion = self.client.chat.completions.create(
               model=self.model,
               messages=[
                   {
                       "role": "system",
                       "content": SYSTEM_PROMPT  # Auto-cached if >1024 tokens
                   },
                   {
                       "role": "user",
                       "content": problem_content
                   }
               ]
           )
   ```

**Expected Savings:**
- Additional 30-50% reduction on input tokens for repeated prompts
- Caching is automatic after first use (5-minute TTL for Claude, automatic for OpenAI)

### Phase 4: Add Model Fallback & Monitoring (Week 4)

**Goal: Ensure reliability and track cost savings**

1. **Implement Fallback Logic**
   ```python
   class LLMServiceFactory:
       @staticmethod
       def create_with_fallback(primary_service, fallback_service):
           """Try primary, fallback to secondary on failure"""
           try:
               return primary_service.generate_solution(...)
           except Exception as e:
               logger.warning(f"Primary service failed: {e}, trying fallback")
               return fallback_service.generate_solution(...)
   ```

2. **Add Cost Tracking**
   ```python
   # api/utils/llm_cost_tracker.py

   class LLMCostTracker:
       PRICES = {
           'gpt-4o': {'input': 2.50, 'output': 10.00},
           'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00},
           'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},
           # ...
       }

       @staticmethod
       def log_usage(model, input_tokens, output_tokens, task_type):
           """Track token usage and cost"""
           cost = (
               input_tokens * PRICES[model]['input'] / 1_000_000 +
               output_tokens * PRICES[model]['output'] / 1_000_000
           )

           # Store in DynamoDB or logs
           logger.info(f"LLM Cost: {model} - {task_type} - ${cost:.4f}")
   ```

---

## Detailed Task-to-Tier Mapping

### Extract Problem Metadata from URL
**Current:** `gemini_service.extract_problem_metadata_from_url()`
**Recommended Tier:** Tier 1 (Flash) for basic info + Tier 2 (Pro) for samples
**Implementation:**
```python
# Split into two calls
basic_info = flash_service.extract_basic_info(url)  # Title, constraints, platform
samples = pro_service.extract_samples(url, basic_info)  # High-precision extraction
```
**Cost Savings:** 60-70%

### Generate Solution Code
**Current:** `openai_service.generate_solution_for_problem()` or `gemini_service.generate_solution_for_problem()`
**Recommended Tier:** Dynamic based on difficulty
- < 1500: Tier 2 (Gemini Pro or Claude Sonnet)
- 1500-2000: Tier 2 (Claude Sonnet)
- 2000+: Tier 3 (GPT-4o or GPT-5)
**Cost Savings:** 50-70%

### Generate Test Case Generator Code
**Current:** `gemini_service.generate_test_case_generator_code()`
**Recommended Tier:** Tier 2 (keep Gemini Pro)
**Cost Savings:** None (already optimal)

### Generate Hints
**Current:** `gemini_service.generate_hints()` (hardcoded Gemini)
**Recommended Tier:** Tier 1 (Gemini Flash) or Tier 2 (Gemini Pro)
**Implementation:**
```python
# Try Flash first for simple hints
flash_hints = flash_service.generate_hints(...)
if not flash_hints or len(flash_hints) < 2:
    # Fallback to Pro for complex analysis
    pro_hints = pro_service.generate_hints(...)
```
**Cost Savings:** 40-60%

---

## Cost Comparison Table

### Per 1000 Problems Processed

| Task | Current Model | Current Cost | Recommended Model | New Cost | Savings |
|------|--------------|--------------|-------------------|----------|---------|
| Basic Metadata | Gemini 2.5 Pro | $6.25 | Gemini 1.5 Flash | $0.50 | 92% |
| Sample Extraction | Gemini 2.5 Pro | $3.75 | Gemini 2.5 Pro | $3.75 | 0% |
| Solution (Easy 40%) | GPT-5 | $80.00 | Gemini 2.5 Pro | $12.00 | 85% |
| Solution (Med 35%) | GPT-5 | $70.00 | Claude Sonnet | $28.00 | 60% |
| Solution (Hard 25%) | GPT-5 | $50.00 | GPT-4o | $15.00 | 70% |
| Test Gen | Gemini 2.5 Pro | $10.00 | Gemini 2.5 Pro | $10.00 | 0% |
| Hints (500 calls) | Gemini 2.5 Pro | $3.75 | Gemini Flash | $0.50 | 87% |
| **TOTAL** | | **$223.75** | | **$69.75** | **69%** |

**Monthly Savings (at 1000 problems/month): $154**
**Annual Savings: $1,848**

---

## Prompt Optimization for Cheaper Models

### For Tier 1 (Simple Extraction)

**Key Principles:**
1. **Be extremely specific** - Cheaper models need clear instructions
2. **Use structured output** - JSON schema or strict format
3. **Minimize context** - Only include relevant information
4. **Add examples** - 1-2 shot examples work well

**Example: Title Extraction with Gemini Flash**
```python
prompt = """Extract ONLY the problem title from this webpage.

RULES:
- Return EXACTLY the title as shown on the page
- Do NOT include problem number or platform name
- Do NOT include any explanation

Format: Return a single line of text

Webpage content:
{content}

Title:"""
```

### For Tier 2 (Balanced)

**Key Principles:**
1. **Clear structure** - Break down complex tasks
2. **Add constraints** - Specify edge cases
3. **Use chain-of-thought** - Ask model to think step by step

**Example: Hint Generation with Gemini Pro**
```python
system_prompt = """You are a competitive programming tutor.

TASK: Generate 3 progressive hints for a student's failing code.

RULES:
1. Hint 1: High-level approach (don't reveal algorithm)
2. Hint 2: Identify specific issue in their code
3. Hint 3: Suggest concrete fix (but no code)

FORMAT: Return JSON array of hint objects"""
```

### For Tier 3 (Complex)

**Key Principles:**
1. **Leverage reasoning** - Use models with built-in reasoning
2. **Provide context** - Include algorithm patterns, edge cases
3. **Iterate on failure** - Build retry logic with error feedback

**Example: Solution Generation with GPT-4o**
```python
system_prompt = """You are a competitive programming expert (rating 3000+).

SOLVE METHODOLOGY:
1. Pattern recognition: Identify problem category
2. Algorithm selection: Choose optimal approach
3. Complexity analysis: Verify time/space constraints
4. Edge case handling: Consider all boundary conditions
5. Implementation: Write production-ready C++ code

For 2500+ difficulty problems, consider advanced techniques:
- DP optimization (Convex Hull Trick, CHT)
- Advanced data structures (Segment Tree, Persistent DS)
- Graph algorithms (Max Flow, Bipartite Matching)

Output: C++ code only, no explanation"""
```

---

## Implementation Checklist

### Phase 1: Infrastructure Setup
- [ ] Add Claude API key to secrets management
- [ ] Create `ClaudeSonnetService` class
- [ ] Create `GeminiFlashService` class
- [ ] Update `LLMServiceFactory` with tier selection logic
- [ ] Add unit tests for new services

### Phase 2: Metadata Extraction Split
- [ ] Implement `extract_basic_info()` with Flash
- [ ] Implement `extract_samples()` with Pro
- [ ] Update `extract_problem_info_task` to use split extraction
- [ ] Test with 10 sample problems
- [ ] Measure cost savings

### Phase 3: Solution Generation Tiers
- [ ] Implement difficulty-based model selection
- [ ] Add fallback logic for service failures
- [ ] Update `generate_solution_with_retry()` to use tiered selection
- [ ] Test across difficulty spectrum (800, 1500, 2000, 2500)
- [ ] Verify solution quality doesn't degrade

### Phase 4: Hint Generation Optimization
- [ ] Implement Flash-based hint generation
- [ ] Add Pro fallback for complex cases
- [ ] Update `generate_hints_task` to use tiered selection
- [ ] Test hint quality

### Phase 5: Prompt Caching
- [ ] Implement prompt caching for Claude
- [ ] Implement prompt caching for OpenAI
- [ ] Extract reusable system prompts to constants
- [ ] Monitor cache hit rates

### Phase 6: Monitoring & Optimization
- [ ] Implement `LLMCostTracker` utility
- [ ] Add cost logging to all LLM calls
- [ ] Create admin dashboard for cost monitoring
- [ ] Set up alerts for cost anomalies
- [ ] Create monthly cost reports

---

## Monitoring & Success Metrics

### Key Performance Indicators (KPIs)

1. **Cost Metrics**
   - Total LLM cost per month
   - Cost per problem extraction
   - Cost per solution generation
   - Cost per hint generation
   - Cost breakdown by model (GPT-4o vs Claude vs Gemini)

2. **Quality Metrics**
   - Solution validation pass rate
   - Sample extraction accuracy (manual review)
   - Hint usefulness rating (user feedback)
   - Time to first correct solution

3. **Performance Metrics**
   - Average latency per task type
   - Cache hit rate (for prompt caching)
   - API error rate by provider
   - Retry rate per model

### Monitoring Dashboard

```python
# Example metrics to track in DynamoDB
{
    'date': '2025-10-11',
    'task_type': 'solution_generation',
    'model': 'gpt-4o',
    'difficulty': 2100,
    'input_tokens': 4500,
    'output_tokens': 3200,
    'cost_usd': 0.043,
    'latency_ms': 15000,
    'success': true,
    'cached': false
}
```

### Alert Thresholds

- **Cost spike**: Daily cost > 2x 7-day average
- **Quality drop**: Validation pass rate < 80%
- **Performance degradation**: Average latency > 30s
- **High retry rate**: Retry rate > 20% for any model

---

## Rollback Plan

If issues arise, rollback can be done incrementally:

1. **Phase 1 Rollback**: Switch metadata extraction back to full Gemini Pro
   - Change: `LLMServiceFactory.create_service('gemini')` instead of Flash
   - No data migration needed

2. **Phase 2 Rollback**: Revert solution generation to GPT-5 only
   - Change: Remove difficulty-based selection logic
   - Set `DEFAULT_LLM_SERVICE = 'openai'`

3. **Phase 3 Rollback**: Disable prompt caching
   - Change: Remove `cache_control` parameters
   - No functionality impact, just cost increase

**Rollback Testing:**
- Keep old service implementations for 2 weeks after launch
- A/B test new tier system with 10% of traffic first
- Monitor quality metrics closely for first week

---

## Future Optimizations

### 1. Fine-tune Smaller Models (3-6 months)
- Collect 500-1000 high-quality problem/solution pairs
- Fine-tune GPT-4o Mini or Claude Haiku for simple extractions
- Expected cost reduction: Additional 40-60% for Tier 1 tasks

### 2. Model Cascading (1-2 months)
- Try cheap model first, escalate on failure
- Example: Flash → Pro → GPT-4o
- Expected cost reduction: 20-30% additional savings

### 3. Batch Processing (2-3 months)
- Batch multiple problems in single API call
- Use Claude's 200K context or Gemini's 2M context
- Expected cost reduction: 15-25% for batch operations

### 4. Self-Hosted Open Models (6-12 months)
- Deploy Llama 3 or Mistral for Tier 1 tasks
- Use GPU instances for inference
- Expected cost reduction: 90% for Tier 1, but requires infrastructure

---

## Recommendations Summary

### Immediate Actions (Week 1)
1. **Add Gemini 1.5 Flash** for basic metadata extraction (92% cost savings)
2. **Implement cost tracking** to establish baseline metrics
3. **Set up monitoring dashboard** for LLM usage

### Short-Term Actions (Month 1)
1. **Add Claude 3.5 Sonnet** for medium-difficulty solutions (60% savings)
2. **Implement difficulty-based routing** for solution generation
3. **Enable prompt caching** for Claude and OpenAI (30-50% additional savings)

### Medium-Term Actions (Quarter 1)
1. **Fine-tune smaller models** for repetitive tasks
2. **Implement model cascading** with automatic fallback
3. **Optimize prompts** based on performance data

### Best Practice Guidelines

1. **Always use the cheapest model that meets quality requirements**
2. **Cache aggressively** - System prompts, few-shot examples, problem context
3. **Monitor quality** - Don't sacrifice accuracy for cost
4. **A/B test** new models before full rollout
5. **Track costs** - Make data-driven decisions

---

## Conclusion

By implementing this 3-tier model selection strategy, Algoitny can reduce LLM costs by **60-75%** while maintaining or improving solution quality:

- **Tier 1 (Gemini Flash)**: Simple extraction tasks → 90% cost reduction
- **Tier 2 (Gemini Pro/Claude Sonnet)**: Moderate tasks → No change or slight improvement
- **Tier 3 (GPT-4o/Claude Sonnet)**: Complex reasoning → 70% cost reduction vs GPT-5

**Total Impact:**
- Monthly cost: $224 → $70 (69% reduction)
- Annual savings: ~$1,850
- Quality: Maintained or improved (especially for hard problems)
- Performance: Similar or better latency

**Next Steps:**
1. Review this document with team
2. Prioritize implementation phases
3. Set up cost tracking baseline
4. Begin Phase 1 implementation (Gemini Flash for metadata)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-11
**Author:** Claude (Anthropic)
**Status:** Draft - Pending Review
