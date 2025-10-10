# GPT-5 Prompt Optimization: Quick Reference Card

## The Problem
- **Gemini**: Minimal prompt → Correct solutions ✓
- **GPT-5**: Verbose prompt → Incorrect solutions ✗

## Root Cause
Treating GPT-5 (reasoning model) like Gemini (deterministic model)

---

## The Fix

### System Context (7 lines)
```python
"""You are an expert competitive programmer solving Codeforces problems (rating ≤2500).

Return ONLY a single C++ code block with no text before or after:

```cpp
// Your solution here
```

Use C++17 standards. Include fast I/O if needed for large inputs."""
```

### User Context (Minimal)
```python
f"""{problem_metadata['title']}

{problem_metadata['constraints']}

Sample Test Cases:
{samples_str}
{retry_context}"""
```

### Retry Context (6 lines)
```python
f"""
Previous attempt failed:
```cpp
{previous_attempt.get('code', 'N/A')}
```

Error: {previous_attempt.get('error', 'Unknown error')}

Fix the issue and provide a corrected solution.
"""
```

---

## What Was Removed

- ❌ Rigid 6-step solving protocol
- ❌ "INTERNAL—DO NOT PRINT" instructions
- ❌ Auto-calculated complexity hints
- ❌ Verbose edge case checklists
- ❌ Multiple output format reminders
- ❌ "Critical Questions" in retry context

## What Was Kept

- ✓ Clear output format requirement (once)
- ✓ Role definition (expert competitive programmer)
- ✓ Technical constraints (C++17, fast I/O)
- ✓ Minimal retry context (code + error + fix instruction)

---

## Why This Works

| Aspect | Old (Failing) | New (Optimized) |
|--------|--------------|-----------------|
| **Philosophy** | "Follow my protocol" | "Solve autonomously" |
| **Prompt Length** | 26 lines | 7 lines |
| **Reasoning Constraints** | Rigid 6-step protocol | None (trusted) |
| **Complexity Hints** | Pre-calculated | Self-calculated |
| **Edge Cases** | Explicit checklist | Implicit reasoning |
| **Alignment with `reasoning_effort="high"`** | Poor | Excellent |
| **Alignment with `verbosity="low"`** | Poor | Excellent |

---

## Key Insight

**GPT-5 with `reasoning_effort="high"` is designed to explore and solve with minimal constraints.**

Verbose prompts interfere with its natural reasoning process.

---

## Testing Checklist

- [ ] Test on 5-10 previously failing problems
- [ ] Compare with old prompt results
- [ ] Check logs for actual prompts sent
- [ ] Measure: Compilation rate, sample pass rate
- [ ] If fails: Try Version 3 (slightly more guidance) or Version 1 (ultra-minimal)

---

## API Configuration (Unchanged)

```python
completion = self.client.responses.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": system_context},
        {"role": "user", "content": user_prompt}
    ],
    reasoning_effort="high",      # Keep - it's GPT-5's strength
    top_p=1,                       # Keep - GPT-5 default
    max_output_tokens=8192,        # Keep - for complex solutions
    text={"verbosity": "low"},     # Keep - now aligned with prompt
    stream=False,
)
```

---

## Expected Improvements

1. **Accuracy** ↑ - Model explores solution space freely
2. **Reasoning Quality** ↑ - No protocol interruptions
3. **Consistency** ↑ - Clear input/output separation
4. **Maintainability** ↑ - Simpler to debug
5. **Speed** ↑ - Less prompt processing overhead

---

## Fallback Versions

### If Version 2 Fails → Try Version 3 (Balanced)
Add minimal requirements list:
1. Analyze problem
2. Ensure time complexity fits limits
3. Use appropriate data types
4. Include fast I/O
5. Return ONLY C++ code block

### If Version 3 Fails → Try Version 1 (Ultra-Minimal)
```python
system_context = """You are an expert competitive programmer solving Codeforces problems.

Output ONLY a C++ code block. No explanations."""
```

---

## Files Modified

**`/Users/gwonsoolee/algoitny/backend/api/services/openai_service.py`**
- Lines 338-350: Simplified retry context (-67%)
- Lines 364-383: Minimal prompts (-73%)
- Removed: Complexity hint calculation (lines 376-389)

---

## Success Criteria

✓ Solutions compile successfully
✓ Sample test cases pass
✓ Correct algorithm selection
✓ Appropriate time complexity
✓ Clean, readable C++ code
✓ No extraneous output

---

## Contact / Questions

See full documentation:
- `/Users/gwonsoolee/algoitny/GPT5_OPTIMIZED_PROMPTS.md` (detailed analysis)
- `/Users/gwonsoolee/algoitny/GPT5_PROMPT_SIMPLIFICATION_SUMMARY.md` (summary)
