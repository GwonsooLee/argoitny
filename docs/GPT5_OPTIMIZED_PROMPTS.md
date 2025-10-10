# GPT-5 Optimized Prompts for Competitive Programming

## Problem Analysis

### Current Issues
1. **Over-constraining reasoning**: Telling GPT-5 HOW to think conflicts with `reasoning_effort="high"`
2. **Verbosity paradox**: Verbose prompt + `verbosity="low"` creates mixed signals
3. **Premature optimization**: Edge case warnings before problem-solving creates decision paralysis
4. **Fighting model strengths**: Rigid protocols prevent natural problem exploration

### Why Minimal Prompts Work Better

GPT-5 with `reasoning_effort="high"`:
- Has sophisticated internal reasoning chains
- Knows competitive programming best practices
- Performs better when trusted to explore the solution space
- Works best with clear constraints on OUTPUT, not on REASONING

## Optimized Prompts

### Version 1: Ultra-Minimal (Gemini-Style)

**System Context:**
```
You are an expert competitive programmer solving Codeforces problems.

Output ONLY a C++ code block. No explanations.
```

**User Context:**
```
Problem: {problem_title}

Input Format:
{constraints}

Sample Test Cases:
{samples}

Language: C++17
```

**Rationale:**
- Trusts GPT-5's reasoning capabilities completely
- No instructions on HOW to think
- Clear OUTPUT constraint only
- Mimics the minimal approach that works for Gemini

---

### Version 2: Minimalist with Output Format (RECOMMENDED)

**System Context:**
```
You are an expert competitive programmer solving Codeforces problems (rating ≤2500).

Return ONLY a single C++ code block with no text before or after:

```cpp
// Your solution here
```

Use C++17 standards. Include fast I/O if needed for large inputs.
```

**User Context:**
```
{problem_title}

{constraints}

Sample Test Cases:
{samples}

{retry_context if applicable}
```

**Rationale:**
- Minimal reasoning constraints
- Clear output format requirement
- Trusts the model to handle complexity analysis, edge cases, algorithm selection
- Works with `reasoning_effort="high"` instead of against it

---

### Version 3: Balanced (If Ultra-Minimal Fails)

**System Context:**
```
You are an expert competitive programmer solving Codeforces problems (rating ≤2500).

Requirements:
1. Analyze the problem and select the optimal algorithm
2. Ensure time complexity fits within typical competitive programming limits (1-2 seconds)
3. Use appropriate data types (long long for large numbers)
4. Include fast I/O for large inputs
5. Return ONLY a C++ code block, no explanations

Output format: Single ```cpp code block, nothing else.
```

**User Context:**
```
Problem: {problem_title}

Input Format and Constraints:
{constraints}

Sample Test Cases:
{samples}

{retry_context if applicable}

Language: C++17 (GNU++17)
```

**Rationale:**
- Slightly more guidance than Version 2
- Still trusts model's reasoning
- Focuses on WHAT to deliver, not HOW to think
- Last resort if minimal versions fail

---

## Retry Context (All Versions)

When `previous_attempt` exists, use this minimal retry context:

```
Previous attempt failed:
{previous_code}

Error: {error_message}

Fix the issue and provide a corrected solution.
```

**Rationale:**
- No need for "Critical Questions" - GPT-5's reasoning will handle root cause analysis
- Direct, factual error presentation
- Trusts model to analyze and correct

---

## API Configuration

```python
completion = self.client.responses.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": system_context},
        {"role": "user", "content": user_prompt}
    ],
    reasoning_effort="high",      # Keep this - it's GPT-5's strength
    top_p=1,                       # Keep default
    max_output_tokens=8192,        # Keep for complex solutions
    text={"verbosity": "low"},     # Keep this - now aligned with minimal prompt
    stream=False,
)
```

**No changes needed to API parameters** - they're already optimal.

---

## Comparison: Current vs Optimized

| Aspect | Current (Failing) | Optimized (Recommended) |
|--------|------------------|------------------------|
| System prompt length | ~26 lines | ~6 lines |
| Reasoning instructions | Rigid 6-step protocol | None (trust model) |
| Edge case warnings | Explicit checklist | Implicit (model knows) |
| Complexity guidance | Prescribed | Implicit (model calculates) |
| Output constraints | Repeated 3+ times | Once, clearly |
| Philosophy | "Follow my protocol" | "Here's the problem, solve it" |
| Alignment with `reasoning_effort="high"` | Poor | Excellent |
| Alignment with `verbosity="low"` | Poor | Excellent |

---

## Expected Improvements

1. **Accuracy**: Model can explore solution space without artificial constraints
2. **Reasoning Quality**: Extended reasoning chains not interrupted by protocol requirements
3. **Consistency**: Clear separation of input (problem) and output (code only)
4. **Simplicity**: Easier to maintain, debug, and understand

---

## Testing Strategy

1. **Start with Version 2 (Recommended)**
2. **If Version 2 produces incomplete solutions, try Version 3**
3. **If Version 3 still fails, try Version 1 (Ultra-Minimal)**
4. **Track success rates** across 10-20 problems
5. **Compare with Gemini** on same problems

---

## Implementation Notes

- The `constraints_hint` calculation (lines 376-389) can be REMOVED - GPT-5 will calculate this internally
- The retry context can be simplified to just code + error
- No need for difficulty-specific prompts - GPT-5 will adapt based on problem complexity
- Trust the model's reasoning capabilities

---

## Key Insight

**Gemini needs explicit step-by-step guidance because it operates at temperature=0.0 with no extended reasoning.**

**GPT-5 with reasoning_effort="high" is fundamentally different - it's designed to explore, reason, and solve with minimal constraints.**

The current prompt treats GPT-5 like Gemini, which is why it fails.
