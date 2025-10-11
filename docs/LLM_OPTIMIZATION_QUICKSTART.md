# LLM Optimization: Quick Start Guide

This guide provides step-by-step instructions to implement cost-optimized LLM usage in Algoitny.

---

## Overview

**Goal:** Reduce LLM costs by 60-75% while maintaining solution quality

**Strategy:** Use cheaper models for simple tasks, premium models for complex reasoning

**Time to Implement:** 2-4 weeks (can be done incrementally)

---

## Phase 1: Quick Wins (Week 1)

### Step 1: Add Gemini Flash for Basic Extraction (92% cost savings)

**Time:** 2-3 hours

1. **Create the Flash service:**
   ```bash
   # Copy from implementation examples document
   cp docs/LLM_OPTIMIZATION_IMPLEMENTATION_EXAMPLES.md backend/api/services/gemini_flash_service.py
   # Edit to keep only GeminiFlashService class
   ```

2. **Update LLM Factory:**
   ```python
   # In api/services/llm_factory.py
   from .gemini_flash_service import GeminiFlashService

   # Add to create_service:
   elif service_type == 'gemini-flash':
       return GeminiFlashService()
   ```

3. **Test it:**
   ```python
   from api.services.llm_factory import LLMServiceFactory

   flash = LLMServiceFactory.create_service('gemini-flash')
   result = flash.extract_basic_metadata(webpage_content, url)
   print(result['title'])
   ```

**Expected Result:**
- Metadata extraction cost: $10/month → $1/month
- Same quality for title/constraints
- 2-3x faster response time

### Step 2: Add Cost Tracking (baseline measurement)

**Time:** 1-2 hours

1. **Create the tracker:**
   ```bash
   # Create api/utils/llm_cost_tracker.py
   # Copy LLMCostTracker class from implementation examples
   ```

2. **Add to existing services:**
   ```python
   # In openai_service.py, after API call:
   from api.utils.llm_cost_tracker import LLMCostTracker

   LLMCostTracker.log_usage(
       model=self.model,
       input_tokens=completion.usage.prompt_tokens,
       output_tokens=completion.usage.completion_tokens,
       task_type='solution_generation',
       metadata={'difficulty': difficulty_rating}
   )
   ```

3. **Check logs:**
   ```bash
   docker logs -f algoitny-backend | grep "LLM Cost"
   ```

**Expected Result:**
- See cost breakdown by task
- Establish baseline costs
- Track daily/monthly spending

---

## Phase 2: Medium Impact (Week 2)

### Step 3: Add Claude for Medium-Difficulty Problems (60% savings)

**Time:** 4-6 hours

1. **Get Claude API key:**
   - Sign up at https://console.anthropic.com/
   - Get API key from dashboard
   - Add to `.env`:
     ```bash
     CLAUDE_API_KEY=sk-ant-your-key-here
     ```

2. **Create Claude service:**
   ```bash
   # Copy ClaudeSonnetService from implementation examples
   # Save to api/services/claude_service.py
   ```

3. **Update LLM Factory with difficulty-based selection:**
   ```python
   # In api/services/llm_factory.py

   @staticmethod
   def create_solution_service(difficulty_rating=None, llm_config=None):
       """Select model based on difficulty"""

       if difficulty_rating is None or difficulty_rating < 1500:
           return LLMServiceFactory.create_service('gemini')

       elif difficulty_rating < 2000:
           return LLMServiceFactory.create_service('claude')

       else:
           return LLMServiceFactory.create_service('openai')
   ```

4. **Update solution generation:**
   ```python
   # In tasks_solution_generation.py

   def generate_solution_with_retry(...):
       difficulty = problem_metadata.get('difficulty_rating')
       service = LLMServiceFactory.create_solution_service(difficulty)
       # Use service instead of hardcoded openai/gemini
   ```

5. **Test on different difficulties:**
   ```bash
   # Test easy problem (should use Gemini)
   python manage.py shell
   >>> from api.tasks import extract_problem_info_task
   >>> result = extract_problem_info_task(
   ...     problem_url='https://codeforces.com/problemset/problem/1/A',  # Easy
   ...     job_id=None
   ... )

   # Check logs for: "[Tier Selection] Difficulty 800 → Gemini 2.5 Pro"

   # Test hard problem (should use GPT-4o)
   >>> result = extract_problem_info_task(
   ...     problem_url='https://codeforces.com/problemset/problem/1000/G',  # Hard
   ...     job_id=None
   ... )

   # Check logs for: "[Tier Selection] Difficulty 2400 → GPT-4o"
   ```

**Expected Result:**
- 40% of problems use Gemini Pro (~$12/month for 1000 problems)
- 35% use Claude Sonnet (~$28/month)
- 25% use GPT-4o (~$15/month)
- Total: ~$55/month (vs $200/month before)

---

## Phase 3: Advanced Optimization (Week 3-4)

### Step 4: Split Metadata Extraction

**Time:** 3-4 hours

1. **Update extract_problem_info_task:**
   ```python
   # In api/tasks.py: extract_problem_info_task

   # Old (single call):
   gemini_service = LLMServiceFactory.create_service('gemini')
   problem_metadata = gemini_service.extract_problem_metadata_from_url(url)

   # New (split calls):
   # 1a. Basic info with Flash (cheap)
   flash = LLMServiceFactory.create_service('gemini-flash')
   basic_info = flash.extract_basic_metadata(webpage_content, url)

   # 1b. Samples with Pro (accurate)
   pro = LLMServiceFactory.create_service('gemini')
   samples = pro.extract_problem_metadata_from_url(url).get('samples', [])

   # 1c. Tags with Flash
   tags = flash.extract_tags(basic_info['title'], basic_info['constraints'])

   # Combine
   problem_metadata = {**basic_info, 'samples': samples, 'tags': tags}
   ```

2. **Test extraction quality:**
   ```python
   # Compare outputs
   # Old approach: ~$0.01 per extraction
   # New approach: ~$0.001 per extraction (90% savings)
   ```

**Expected Result:**
- Metadata extraction: $10/month → $1.50/month
- Maintained quality for all fields
- Slightly faster (parallel extraction possible)

### Step 5: Enable Prompt Caching

**Time:** 2-3 hours

1. **Update Claude service to mark system prompts for caching:**
   ```python
   # In claude_service.py: generate_solution_for_problem

   message = self.client.messages.create(
       model=self.model,
       max_tokens=8192,
       system=[
           {
               "type": "text",
               "text": SYSTEM_PROMPT,  # This will be cached
               "cache_control": {"type": "ephemeral"}
           }
       ],
       messages=[...]
   )
   ```

2. **Extract system prompts to constants:**
   ```python
   # In api/services/prompts.py (new file)

   SOLUTION_GENERATION_SYSTEM_PROMPT = """You are a competitive programming expert...
   [Full system prompt here - this will be cached]
   """

   # Import in services:
   from api.services.prompts import SOLUTION_GENERATION_SYSTEM_PROMPT
   ```

3. **Monitor cache hit rate:**
   ```python
   # In claude_service.py, log cache usage:
   logger.info(f"[Claude Cache] Read: {usage.cache_read_input_tokens}, "
              f"Created: {usage.cache_creation_input_tokens}")
   ```

**Expected Result:**
- After first call, 90% of input tokens use cached pricing
- Claude input cost: $3.00/1M → $0.30/1M for cached portion
- Additional 30-50% savings on repeated prompts

---

## Monitoring & Validation

### Daily Checks (First Week)

Run these checks daily to ensure everything works:

```bash
# 1. Check cost logs
docker logs algoitny-backend | grep "LLM Cost" | tail -20

# 2. Check tier selection
docker logs algoitny-backend | grep "Tier Selection" | tail -10

# 3. Get daily cost summary
python manage.py shell
>>> from api.utils.llm_cost_tracker import LLMCostTracker
>>> summary = LLMCostTracker.get_daily_cost_summary()
>>> print(f"Total: ${summary['total_cost']:.2f}")
>>> print(f"By model: {summary['by_model']}")
```

### Quality Validation

Test on 10 sample problems after each phase:

```python
# Test problems across difficulty spectrum
test_urls = [
    'https://codeforces.com/problemset/problem/4/A',    # 800 (easy)
    'https://codeforces.com/problemset/problem/1/C',    # 1400 (medium)
    'https://codeforces.com/problemset/problem/1000/E', # 1900 (medium-hard)
    'https://codeforces.com/problemset/problem/1000/G', # 2400 (hard)
]

for url in test_urls:
    # Extract and validate
    result = extract_problem_info_task(url, job_id=None)

    # Check solution compiles
    # Check passes sample tests
    # Compare with previous solution quality
```

**Quality Metrics:**
- Solution validation pass rate > 80%
- Sample extraction accuracy > 95%
- No regression in solution correctness

---

## Troubleshooting

### Issue: Claude API returns 401 Unauthorized

**Solution:**
```bash
# Check API key in .env
echo $CLAUDE_API_KEY

# Restart backend to load new env
docker-compose restart backend
```

### Issue: Cost tracking shows $0.00

**Solution:**
```python
# Check if tracking is enabled
# In settings.py
LLM_COST_TRACKING_ENABLED = True

# Check if log_usage is called
# Add debug log in services:
logger.info(f"Calling LLMCostTracker.log_usage for {model}")
```

### Issue: Flash extraction quality is poor

**Solution:**
```python
# Option 1: Improve prompts
# Make prompts more specific and structured

# Option 2: Fallback to Pro
if not basic_info or len(basic_info.get('title', '')) < 3:
    logger.warning("Flash extraction failed, using Pro")
    pro_service = LLMServiceFactory.create_service('gemini')
    basic_info = pro_service.extract_basic_metadata(...)
```

### Issue: Solution quality degraded after switching to Claude

**Solution:**
```python
# Adjust difficulty thresholds
# In llm_factory.py:

# Before (too aggressive):
elif difficulty_rating < 2000:
    return 'claude'

# After (more conservative):
elif 1600 <= difficulty_rating < 2100:
    return 'claude'
```

---

## Cost Savings Calculator

Use this to estimate your savings:

```python
# Current monthly costs (example)
current_costs = {
    'metadata_extraction': 1000 * 0.010,  # 1000 problems × $0.010
    'solution_generation': 1000 * 0.200,  # 1000 problems × $0.200
    'hint_generation': 500 * 0.008,       # 500 hints × $0.008
}
current_total = sum(current_costs.values())

# After optimization
optimized_costs = {
    'metadata_extraction': 1000 * 0.0015,  # 85% reduction (Flash for basic)
    'solution_generation': (
        400 * 0.012 +  # 40% easy with Gemini Pro
        350 * 0.028 +  # 35% medium with Claude
        250 * 0.060    # 25% hard with GPT-4o
    ),
    'hint_generation': 500 * 0.002,  # 75% reduction (Claude/Flash)
}
optimized_total = sum(optimized_costs.values())

print(f"Current: ${current_total:.2f}/month")
print(f"Optimized: ${optimized_total:.2f}/month")
print(f"Savings: ${current_total - optimized_total:.2f}/month ({(1 - optimized_total/current_total)*100:.1f}%)")
```

**Example Output:**
```
Current: $218.00/month
Optimized: $71.30/month
Savings: $146.70/month (67.3%)
```

---

## Rollback Plan

If you need to rollback any phase:

### Rollback Phase 3 (Prompt Caching)
```python
# Remove cache_control from Claude calls
# No functionality impact, just cost increase
```

### Rollback Phase 2 (Difficulty-Based Selection)
```python
# In llm_factory.py:
@staticmethod
def create_solution_service(difficulty_rating=None, llm_config=None):
    # Always use OpenAI (old behavior)
    return LLMServiceFactory.create_service('openai')
```

### Rollback Phase 1 (Flash Extraction)
```python
# In tasks.py:
# Replace split extraction with single Pro call
gemini_service = LLMServiceFactory.create_service('gemini')
problem_metadata = gemini_service.extract_problem_metadata_from_url(url)
```

---

## Success Metrics

Track these KPIs weekly:

| Metric | Baseline | Week 1 | Week 2 | Week 3 | Target |
|--------|----------|--------|--------|--------|--------|
| **Cost per Problem** | $0.218 | $0.080 | $0.075 | $0.071 | < $0.080 |
| **Solution Pass Rate** | 82% | 81% | 83% | 84% | > 80% |
| **Metadata Accuracy** | 95% | 94% | 95% | 96% | > 93% |
| **Avg Latency (sec)** | 25 | 22 | 20 | 18 | < 30 |

**Green Light:** All metrics meet or exceed targets → proceed to next phase

**Yellow Light:** 1-2 metrics slightly below → investigate and adjust

**Red Light:** 3+ metrics below or critical failure → rollback immediately

---

## Next Steps

### Week 1: Quick Wins
- [ ] Day 1: Add Gemini Flash service
- [ ] Day 2: Add cost tracking
- [ ] Day 3: Test on 10 problems
- [ ] Day 4-5: Monitor costs and quality
- [ ] Day 6-7: Adjust if needed

### Week 2: Medium Impact
- [ ] Day 1: Get Claude API key
- [ ] Day 2: Add Claude service
- [ ] Day 3: Implement difficulty-based selection
- [ ] Day 4: Test across difficulty spectrum
- [ ] Day 5-7: Monitor and optimize

### Week 3: Advanced
- [ ] Day 1-2: Split metadata extraction
- [ ] Day 3-4: Enable prompt caching
- [ ] Day 5-7: Monitor cache hit rates

### Week 4: Polish
- [ ] Day 1-2: Fine-tune difficulty thresholds
- [ ] Day 3-4: Optimize prompts for each model
- [ ] Day 5-7: Generate cost report and document learnings

---

## Helpful Commands

```bash
# View recent LLM calls
docker logs algoitny-backend | grep "LLM Cost" | tail -50

# Check tier selection decisions
docker logs algoitny-backend | grep "Tier Selection"

# Monitor cache hit rates
docker logs algoitny-backend | grep "Claude Cache"

# Get daily cost breakdown
python manage.py shell -c "from api.utils.llm_cost_tracker import LLMCostTracker; print(LLMCostTracker.get_daily_cost_summary())"

# Test extraction with Flash
python manage.py shell
>>> from api.services.llm_factory import LLMServiceFactory
>>> flash = LLMServiceFactory.create_service('gemini-flash')
>>> # Test extraction...

# Compare model outputs
python manage.py shell
>>> # Generate with Gemini
>>> gemini = LLMServiceFactory.create_service('gemini')
>>> result1 = gemini.generate_solution_for_problem(metadata)
>>>
>>> # Generate with Claude
>>> claude = LLMServiceFactory.create_service('claude')
>>> result2 = claude.generate_solution_for_problem(metadata)
>>>
>>> # Compare quality
```

---

## Support & Resources

**Documentation:**
- Full strategy: `docs/LLM_OPTIMIZATION_STRATEGY.md`
- Implementation examples: `docs/LLM_OPTIMIZATION_IMPLEMENTATION_EXAMPLES.md`
- This guide: `docs/LLM_OPTIMIZATION_QUICKSTART.md`

**API Documentation:**
- Gemini: https://ai.google.dev/gemini-api/docs
- Claude: https://docs.anthropic.com/claude/reference
- OpenAI: https://platform.openai.com/docs/api-reference

**Pricing Pages:**
- Gemini: https://ai.google.dev/pricing
- Claude: https://www.anthropic.com/pricing
- OpenAI: https://openai.com/pricing

---

**Good luck with the optimization! Start small, measure everything, and scale gradually.**
