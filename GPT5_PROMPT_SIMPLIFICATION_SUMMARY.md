# GPT-5 Prompt Simplification: Summary of Changes

## Problem Statement

GPT-5 with elaborate, detailed prompts was producing **incorrect solutions**, while Gemini with minimal prompting (just raw problem text) was producing **correct solutions**.

## Root Cause Analysis

### Why Verbose Prompts Hurt GPT-5

1. **Reasoning Mode Conflict**:
   - GPT-5 uses `reasoning_effort="high"` with extended internal reasoning chains
   - Prescriptive protocols (6-step SOLVING PROTOCOL) interfere with the model's natural reasoning
   - Instructions like "INTERNAL—DO NOT PRINT" are redundant and confusing

2. **Verbosity Paradox**:
   - API setting: `text={"verbosity": "low"}`
   - Prompt: 26 lines of verbose instructions
   - **Conflict**: Model receives mixed signals about output expectations

3. **Over-Constraint**:
   - Premature edge case warnings create decision paralysis
   - Rigid protocol prevents natural problem exploration
   - Complexity hints calculated before reasoning may bias solution approach

4. **Fighting Model Strengths**:
   - GPT-5 is designed to explore solution spaces with minimal constraints
   - Current prompt treats it like a rule-following system, not a reasoning system

## Solution: Minimal Trust-Based Prompts

### Before (Failing - 26 lines)

```python
system_context = """You are a competitive programming solver for Codeforces (rating <=2500).
Follow the SOLVING PROTOCOL INTERNALLY, but OUTPUT ONLY THE FINAL C++ CODE BLOCK.

HARD OUTPUT RULES (highest priority):
- Return EXACTLY ONE fenced code block in C++ (```cpp ... ```), with no text before/after.
- If there is any risk of exceeding token limits, SKIP ALL EXPLANATIONS and output only the final code.
- If constraints are missing, assume TL=1–2s, ML=256–512MB, n,q≤2e5, and choose an algorithm that safely fits those.

SOLVING PROTOCOL (INTERNAL—DO NOT PRINT):
0) Restate problem in 2–3 lines (internally only).
1) Identify pattern/category (DS, Graph, DP, Math, etc.).
2) Choose an algorithm with provable complexity; ensure it fits constraints (O(n log n) typical).
   - Do the back-of-the-envelope op-count check internally.
3) Edge cases & pitfalls checklist (internally):
   - 64-bit overflows; off-by-one; empty/min/max; duplicates; recursion depth; I/O speed; strict output format.
4) Implementation plan (internally): data types, I/O, structure, failure modes.
5) Final Code: C++17/20 single file.
   - Fast IO: ios::sync_with_stdio(false); cin.tie(nullptr);
   - Avoid recursion if depth may exceed 1e5; prefer iterative.
   - No debug prints; deterministic behavior.
   - Minimal top-of-file comment (≤8 lines) summarizing approach & complexity only.

If problem statement is ambiguous, make the least-risk assumption and add ONE short comment line about it at the top of the code.

If you accidentally include any prose outside the code block, REGENERATE and return only the code block.

OUTPUT FORMAT (repeat): Only one C++ fenced code block, nothing else."""
```

### After (Optimized - 7 lines)

```python
system_context = """You are an expert competitive programmer solving Codeforces problems (rating ≤2500).

Return ONLY a single C++ code block with no text before or after:

```cpp
// Your solution here
```

Use C++17 standards. Include fast I/O if needed for large inputs."""
```

**Reduction**: 26 lines → 7 lines (73% reduction)

---

### User Prompt Changes

#### Before (Failing)

```python
user_prompt = f"""Problem:
Title: {problem_metadata['title']}

Input Format and Constraints:
{problem_metadata['constraints']}{constraints_hint}  # Auto-calculated complexity hint

Sample Test Cases:
{samples_str}

{retry_context}  # Verbose 18-line analysis with "Critical Questions"

Language: C++17 (GNU++17)"""
```

#### After (Optimized)

```python
user_prompt = f"""{problem_metadata['title']}

{problem_metadata['constraints']}

Sample Test Cases:
{samples_str}
{retry_context}"""  # Minimal: just code, error, and "Fix it"
```

**Changes**:
- Removed "Problem:", "Title:", "Input Format and Constraints:" labels
- Removed auto-calculated complexity hints (GPT-5 will calculate internally)
- Removed "Language: C++17" (implied from system context)
- Simplified retry context from 18 lines to 6 lines

---

### Retry Context Changes

#### Before (Failing - 18 lines)

```python
retry_context = f"""
## PREVIOUS ATTEMPT ANALYSIS
Your previous solution FAILED. Analyze your mistake:

### Previous Code:
```cpp
{previous_attempt.get('code', 'N/A')}
```

### Failure Reason:
{previous_attempt.get('error', 'Unknown error')}

### Critical Questions:
1. **Algorithm Selection**: Was your algorithm correct for this problem type?
2. **Time Complexity**: Did you exceed time limits? What's the required complexity?
3. **Edge Cases**: Which edge case did you miss?
4. **Implementation Bugs**: Off-by-one errors? Integer overflow? Array bounds?

### Your Task Now:
Generate a CORRECTED solution that fixes the specific failure above.
"""
```

#### After (Optimized - 6 lines)

```python
retry_context = f"""
Previous attempt failed:
```cpp
{previous_attempt.get('code', 'N/A')}
```

Error: {previous_attempt.get('error', 'Unknown error')}

Fix the issue and provide a corrected solution.
"""
```

**Reduction**: 18 lines → 6 lines (67% reduction)

**Rationale**: GPT-5's extended reasoning will handle root cause analysis better than prescribed questions.

---

## Removed Features

### 1. Auto-Calculated Complexity Hints (Lines 376-389)

**Removed Code**:
```python
constraints_hint = ""
constraints_text = problem_metadata.get('constraints', '')
n_match = re.search(r'[1≤]\s*N\s*[≤]\s*(\d+)', constraints_text)
if n_match:
    max_n = int(n_match.group(1))
    if max_n <= 500:
        constraints_hint = "\n**Complexity Target:** O(N³) may be acceptable for N ≤ 500"
    elif max_n <= 5000:
        constraints_hint = "\n**Complexity Target:** O(N²) acceptable for N ≤ 5000"
    elif max_n <= 100000:
        constraints_hint = "\n**Complexity Target:** O(N log N) or O(N) required for N ≤ 10⁵"
    else:
        constraints_hint = "\n**Complexity Target:** O(N) or O(log N) required for large N"
```

**Rationale**:
- GPT-5's reasoning will calculate this more accurately
- Premature hints may bias the solution approach
- Constraints already contain N values; model can extract them

### 2. Rigid 6-Step Solving Protocol

**Removed**:
- "0) Restate problem in 2–3 lines"
- "1) Identify pattern/category"
- "2) Choose algorithm with provable complexity"
- "3) Edge cases & pitfalls checklist"
- "4) Implementation plan"
- "5) Final Code"

**Rationale**:
- GPT-5's internal reasoning already does this
- Prescribing steps interferes with natural reasoning flow
- `reasoning_effort="high"` is designed for autonomous exploration

### 3. Verbose Output Format Reminders

**Removed**:
- "HARD OUTPUT RULES (highest priority)"
- "If there is any risk of exceeding token limits..."
- "If you accidentally include any prose outside the code block, REGENERATE..."
- "OUTPUT FORMAT (repeat): Only one C++ fenced code block, nothing else."

**Kept**: Single clear instruction in system context
- "Return ONLY a single C++ code block with no text before or after:"

**Rationale**: One clear instruction > Multiple reminders

---

## Key Differences: GPT-5 vs Gemini

| Aspect | Gemini | GPT-5 |
|--------|--------|-------|
| **Reasoning Mode** | No extended reasoning | `reasoning_effort="high"` |
| **Temperature** | 0.0 (deterministic) | Default (with reasoning) |
| **Optimal Prompt Length** | Verbose (143 lines) | Minimal (7 lines) |
| **Guidance Needed** | Explicit step-by-step | Trust-based minimal |
| **Philosophy** | "Follow this protocol" | "Here's the problem, solve it" |
| **Edge Case Handling** | Explicit checklist | Implicit reasoning |
| **Complexity Calculation** | Provided as hint | Self-calculated |

**Key Insight**: Gemini and GPT-5 are fundamentally different models requiring opposite prompting strategies.

---

## Expected Improvements

1. **Accuracy**: ↑ (Model explores solution space without artificial constraints)
2. **Reasoning Quality**: ↑ (Extended reasoning not interrupted by protocol)
3. **Consistency**: ↑ (Clear separation of input/output expectations)
4. **Maintainability**: ↑ (Simpler prompts easier to debug)
5. **Alignment**: ↑ (Prompt now aligned with `reasoning_effort="high"` and `verbosity="low"`)

---

## Testing Recommendations

1. **Immediate Testing**: Try 5-10 problems that previously failed with GPT-5
2. **Comparison**: Run same problems on both old and new prompts
3. **Success Metrics**:
   - Compilation success rate
   - Sample test case pass rate
   - Full test suite pass rate (if available)
4. **Fallback Plan**: If minimal prompt fails on specific problem types, add targeted guidance (NOT general protocol)

---

## Fallback Strategy

If Version 2 (current implementation) produces incomplete solutions:

### Version 3: Slightly More Guidance

```python
system_context = """You are an expert competitive programmer solving Codeforces problems (rating ≤2500).

Requirements:
1. Analyze the problem and select the optimal algorithm
2. Ensure time complexity fits within typical competitive programming limits (1-2 seconds)
3. Use appropriate data types (long long for large numbers)
4. Include fast I/O for large inputs
5. Return ONLY a C++ code block, no explanations

Output format: Single ```cpp code block, nothing else."""
```

### Version 1: Ultra-Minimal (Last Resort)

```python
system_context = """You are an expert competitive programmer solving Codeforces problems.

Output ONLY a C++ code block. No explanations."""

user_prompt = f"""{problem_metadata['title']}

{problem_metadata['constraints']}

{samples_str}
{retry_context}"""
```

---

## Files Modified

### `/Users/gwonsoolee/algoitny/backend/api/services/openai_service.py`

**Lines Changed**:
- 338-350: Simplified retry context
- 352-383: Replaced verbose prompts with minimal versions
- Removed: Lines 376-389 (complexity hint calculation)

**Total Changes**:
- System context: 26 lines → 7 lines (-73%)
- Retry context: 18 lines → 6 lines (-67%)
- Removed complexity hint calculation: 14 lines

---

## Documentation Created

1. **`/Users/gwonsoolee/algoitny/GPT5_OPTIMIZED_PROMPTS.md`**
   - Comprehensive analysis of prompt optimization
   - Three versions (Ultra-Minimal, Recommended, Balanced)
   - Comparison tables and rationale

2. **`/Users/gwonsoolee/algoitny/GPT5_PROMPT_SIMPLIFICATION_SUMMARY.md`** (this file)
   - Quick reference for changes
   - Before/after comparisons
   - Testing recommendations

---

## Next Steps

1. **Test Immediately**: Run 5-10 previously failing problems
2. **Monitor Logs**: Check `logger.info()` output to see actual prompts sent
3. **Compare Results**: Note improvements in solution quality
4. **Document Findings**: Track which problem types benefit most
5. **Iterate**: If needed, adjust to Version 3 or Version 1 based on results

---

## Conclusion

**The Problem**: Treating GPT-5 like Gemini with verbose, prescriptive prompts

**The Solution**: Trust GPT-5's reasoning capabilities with minimal, focused prompts

**The Philosophy**: Let the model explore, reason, and solve autonomously while providing clear output constraints

**Expected Outcome**: Higher accuracy, better reasoning, and more reliable solutions
