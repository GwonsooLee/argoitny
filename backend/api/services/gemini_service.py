"""Gemini AI Service"""
import json
import requests
import google.generativeai as genai
from django.conf import settings


class GeminiService:
    """Handle Gemini AI operations"""

    # Few-shot examples database for 2500+ difficulty problems
    FEW_SHOT_EXAMPLES = {
        'dp_optimization': {
            'description': 'DP optimization techniques (Convex Hull Trick, Divide & Conquer DP, etc.)',
            'when_to_use': 'DP with transitions of form dp[i] = min/max(dp[j] + cost(j, i)) where cost is linear or quadratic',
            'time_complexity': 'O(N log N) instead of O(N²)',
            'code_pattern': '''// Convex Hull Trick for DP optimization
struct Line {
    long long m, c;
    long long eval(long long x) { return m * x + c; }
};

deque<Line> hull;

bool bad(Line l1, Line l2, Line l3) {
    // Check if l2 is redundant
    return (__int128)(l3.c - l1.c) * (l1.m - l2.m) <= (__int128)(l2.c - l1.c) * (l1.m - l3.m);
}

void addLine(Line newLine) {
    while (hull.size() >= 2 && bad(hull[hull.size()-2], hull[hull.size()-1], newLine))
        hull.pop_back();
    hull.push_back(newLine);
}

long long query(long long x) {
    while (hull.size() >= 2 && hull[0].eval(x) >= hull[1].eval(x))
        hull.pop_front();
    return hull[0].eval(x);
}'''
        },
        'segment_tree': {
            'description': 'Segment Tree with Lazy Propagation for range updates/queries',
            'when_to_use': 'Range update + range query operations',
            'time_complexity': 'O(log N) per operation',
            'code_pattern': '''// Segment Tree with Lazy Propagation
const int MAXN = 200005;
long long tree[4*MAXN], lazy[4*MAXN];

void push(int node, int start, int end) {
    if (lazy[node] != 0) {
        tree[node] += (end - start + 1) * lazy[node];
        if (start != end) {
            lazy[2*node] += lazy[node];
            lazy[2*node+1] += lazy[node];
        }
        lazy[node] = 0;
    }
}

void updateRange(int node, int start, int end, int l, int r, long long val) {
    push(node, start, end);
    if (start > r || end < l) return;
    if (start >= l && end <= r) {
        lazy[node] += val;
        push(node, start, end);
        return;
    }
    int mid = (start + end) / 2;
    updateRange(2*node, start, mid, l, r, val);
    updateRange(2*node+1, mid+1, end, l, r, val);
    push(2*node, start, mid);
    push(2*node+1, mid+1, end);
    tree[node] = tree[2*node] + tree[2*node+1];
}'''
        },
        'graph_flows': {
            'description': 'Maximum flow (Dinic\'s Algorithm) and bipartite matching',
            'when_to_use': 'Maximum bipartite matching or maximum flow problems',
            'time_complexity': 'O(V²E) for Dinic',
            'code_pattern': '''// Dinic's Algorithm for Maximum Flow
const long long INF = 1e18;

struct Edge {
    int to, rev;
    long long cap;
};

vector<Edge> graph[MAXN];
int level[MAXN], iter[MAXN];

void addEdge(int from, int to, long long cap) {
    graph[from].push_back({to, (int)graph[to].size(), cap});
    graph[to].push_back({from, (int)graph[from].size()-1, 0});
}

bool bfs(int s, int t) {
    memset(level, -1, sizeof(level));
    queue<int> q;
    level[s] = 0;
    q.push(s);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (auto& e : graph[v]) {
            if (e.cap > 0 && level[e.to] < 0) {
                level[e.to] = level[v] + 1;
                q.push(e.to);
            }
        }
    }
    return level[t] >= 0;
}

long long dfs(int v, int t, long long f) {
    if (v == t) return f;
    for (int& i = iter[v]; i < graph[v].size(); i++) {
        Edge& e = graph[v][i];
        if (e.cap > 0 && level[v] < level[e.to]) {
            long long d = dfs(e.to, t, min(f, e.cap));
            if (d > 0) {
                e.cap -= d;
                graph[e.to][e.rev].cap += d;
                return d;
            }
        }
    }
    return 0;
}'''
        },
        'string_algorithms': {
            'description': 'Advanced string algorithms (KMP, Z-algorithm, etc.)',
            'when_to_use': 'Pattern matching, string searching, prefix/suffix operations',
            'time_complexity': 'O(N + M) for KMP',
            'code_pattern': '''// KMP Algorithm for pattern matching
vector<int> computeLPS(string pattern) {
    int m = pattern.length();
    vector<int> lps(m);
    int len = 0;
    lps[0] = 0;
    int i = 1;

    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        } else {
            if (len != 0) {
                len = lps[len - 1];
            } else {
                lps[i] = 0;
                i++;
            }
        }
    }
    return lps;
}

vector<int> KMP(string text, string pattern) {
    vector<int> lps = computeLPS(pattern);
    vector<int> matches;
    int n = text.length();
    int m = pattern.length();
    int i = 0, j = 0;

    while (i < n) {
        if (pattern[j] == text[i]) {
            i++;
            j++;
        }
        if (j == m) {
            matches.push_back(i - j);
            j = lps[j - 1];
        } else if (i < n && pattern[j] != text[i]) {
            if (j != 0) {
                j = lps[j - 1];
            } else {
                i++;
            }
        }
    }
    return matches;
}'''
        }
    }

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
        else:
            self.model = None

    def get_optimal_temperature(self, difficulty_rating):
        """
        Get optimal temperature based on problem difficulty
        Lower temperature = more deterministic (better for hard problems)
        Higher temperature = more creative (better for easy problems)
        """
        if difficulty_rating is None:
            return 0.7  # Default
        elif difficulty_rating >= 2500:
            return 0.3  # Very deterministic for 2500+ problems
        elif difficulty_rating >= 2000:
            return 0.5
        elif difficulty_rating >= 1500:
            return 0.7
        else:
            return 0.8

    def get_difficulty_guidance(self, difficulty_rating):
        """Generate difficulty-specific guidance for prompts"""
        if difficulty_rating is None:
            return ""

        if difficulty_rating >= 2500:
            return """
## DIFFICULTY LEVEL: 2500+ (Very Hard / Expert)
⚠️ This is an ADVANCED problem requiring expert-level competitive programming skills.

Expected solution characteristics:
- **Algorithm**: Advanced data structures or algorithms (segment trees, DP optimization, FFT, suffix arrays, graph flows, etc.)
- **Time Complexity**: Must be near-optimal (often O(N log N) or O(N))
- **Common patterns**: DP optimization, advanced graph algorithms, number theory, computational geometry, string algorithms
- **Edge cases**: Requires EXTREMELY careful handling of boundary conditions, integer overflow, and special cases
- **Proof**: Solution often requires mathematical proof or deep algorithmic insight

### Critical Analysis Required:
1. **Problem Pattern Recognition**: Does this match a known hard problem pattern?
2. **Algorithm Selection**: Which advanced technique is needed?
3. **Implementation Complexity**: Are there subtle implementation details that can break the solution?
4. **Edge Case Explosion**: What are ALL the edge cases for this specific problem?
"""
        elif difficulty_rating >= 2000:
            return """
## DIFFICULTY LEVEL: 2000-2499 (Hard)
This is a CHALLENGING problem requiring solid competitive programming skills.

Expected solution characteristics:
- **Algorithm**: Advanced DP, graph algorithms, or data structures
- **Time Complexity**: Usually O(N log N) or O(N²) with small constant
- **Common patterns**: Complex DP, greedy with proof, binary search, graph traversal with state
"""
        elif difficulty_rating >= 1500:
            return """
## DIFFICULTY LEVEL: 1500-1999 (Medium-Hard)
This is an INTERMEDIATE problem requiring good problem-solving skills.

Expected solution characteristics:
- **Algorithm**: DP, BFS/DFS, sorting, binary search, or moderate data structures
- **Time Complexity**: O(N log N) or O(N²) acceptable
"""
        else:
            return """
## DIFFICULTY LEVEL: Below 1500 (Easy-Medium)
This is a BEGINNER-FRIENDLY problem.

Expected solution characteristics:
- **Algorithm**: Simple implementation, brute force with optimization, or basic algorithms
- **Time Complexity**: O(N) to O(N²) typically acceptable
"""

    def get_algorithm_hints(self, difficulty_rating):
        """Get algorithm hints for 2500+ problems"""
        if difficulty_rating is None or difficulty_rating < 2500:
            return ""

        return """
### Advanced Algorithm Patterns for 2500+ Problems

Consider these advanced techniques and patterns:

**1. Dynamic Programming Optimization**
- Convex Hull Trick: For DP with linear transitions
- Divide & Conquer DP: For DP with quadrilateral inequality
- Knuth's Optimization: For specific DP recurrences
- Slope Trick: For maintaining piecewise linear functions

**2. Advanced Data Structures**
- Segment Tree with Lazy Propagation: Range updates and queries
- Persistent Data Structures: Access previous versions
- Heavy-Light Decomposition: Tree path queries
- Link-Cut Tree: Dynamic tree queries
- Fenwick Tree (BIT): Range sum queries

**3. Graph Algorithms**
- Maximum Flow: Dinic's algorithm, min-cost max-flow
- Bipartite Matching: Hungarian algorithm, Hopcroft-Karp
- Strongly Connected Components: Tarjan's, Kosaraju's
- Articulation Points and Bridges
- Lowest Common Ancestor (LCA): Binary lifting, Euler tour

**4. String Algorithms**
- KMP, Z-algorithm: Pattern matching
- Suffix Array, Suffix Automaton: String indexing
- Aho-Corasick: Multiple pattern matching
- Manacher's Algorithm: Palindrome detection
- Rolling Hash: Fast string comparison

**5. Mathematics & Number Theory**
- Modular Arithmetic: Extended Euclidean, modular inverse
- Prime Factorization: Pollard's rho
- Combinatorics: Lucas theorem, Catalan numbers
- FFT/NTT: Fast polynomial multiplication
- Matrix Exponentiation: Linear recurrence optimization

**6. Computational Geometry**
- Convex Hull: Graham scan, Jarvis march
- Line Sweep: Closest pair, segment intersection
- Rotating Calipers: Farthest pair
"""

    def get_few_shot_examples(self, algorithm_category, difficulty_rating):
        """
        Get few-shot examples based on algorithm category
        Only returns examples for 2500+ problems
        """
        if difficulty_rating is None or difficulty_rating < 2500:
            return ""

        if algorithm_category not in self.FEW_SHOT_EXAMPLES:
            return ""

        example = self.FEW_SHOT_EXAMPLES[algorithm_category]

        return f"""
## Few-Shot Example: {example['description']}

**When to use:** {example['when_to_use']}
**Time Complexity:** {example['time_complexity']}

**Code Pattern:**
```cpp
{example['code_pattern']}
```
"""

    def analyze_problem_category(self, problem_metadata):
        """
        Analyze problem and identify algorithm category for few-shot selection
        Returns category string or None
        """
        if not self.model:
            return None

        import logging
        logger = logging.getLogger(__name__)

        try:
            # Quick analysis prompt
            analysis_prompt = f"""Analyze this competitive programming problem and identify the PRIMARY algorithm/data structure needed.

Problem: {problem_metadata.get('title', 'Unknown')}
Constraints: {problem_metadata.get('constraints', 'Unknown')[:500]}

Return ONLY ONE of these categories:
- dp_optimization (DP requiring CHT, divide-and-conquer, or Knuth optimization)
- segment_tree (range queries/updates)
- graph_flows (max flow, bipartite matching)
- string_algorithms (KMP, suffix array, etc.)
- graph_basic (BFS, DFS, shortest path)
- dp_basic (standard DP)
- greedy (greedy algorithm)
- math (number theory, combinatorics)
- implementation (simulation, brute force)

Return ONLY the category name, nothing else."""

            response = self.model.generate_content(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for deterministic category
                )
            )
            category = response.text.strip().lower()
            logger.info(f"Problem category detected: {category}")
            return category

        except Exception as e:
            logger.warning(f"Failed to analyze problem category: {e}")
            return None

    def generate_test_case_generator_code(self, problem_info, previous_failure=None):
        """
        Generate Python code that will generate test cases

        Args:
            problem_info: Dict containing:
                - platform: str
                - problem_id: str
                - title: str
                - solution_code: str (optional, for reference)
                - language: str
                - constraints: str
            previous_failure: Dict containing (optional):
                - code: str (previously generated code that failed)
                - error: str (error message from the failure)

        Returns:
            str: Python code that generates test cases

        Raises:
            ValueError: If API key not configured or generation fails
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        # Include solution code in prompt if available
        solution_code_section = ""
        if problem_info.get('solution_code'):
            solution_code_section = f"""
Solution Code (for understanding input format):
```{problem_info['language']}
{problem_info['solution_code']}
```

ANALYZE THIS CODE CAREFULLY to understand:
1. Is it single test case or multiple test cases?
   - If main() reads `int t` and has a loop, it's MULTI-TEST CASE format
   - If main() directly processes input, it's SINGLE TEST case format
2. What is the EXACT input format for each test case?
3. What is the order of inputs?
"""

        # Include previous failure context if available
        previous_failure_section = ""
        if previous_failure and previous_failure.get('code') and previous_failure.get('error'):
            previous_failure_section = f"""
⚠️ PREVIOUS ATTEMPT FAILED - LEARN FROM THIS MISTAKE:

Previously Generated Code:
```python
{previous_failure['code']}
```

Error That Occurred:
{previous_failure['error']}

IMPORTANT: Analyze what went wrong in the previous attempt and FIX the issue in your new code.
Common issues to check:
1. Was the input format incorrect?
2. Were the constraints violated?
3. Was the multi-test case format handled correctly?
4. Were there any syntax errors or logic errors?

Generate NEW, CORRECTED code that addresses the failure above.
"""

        prompt = f"""You are an expert at creating test case generators for competitive programming problems.
{previous_failure_section}

Problem Details:
- Platform: {problem_info['platform']}
- Problem ID: {problem_info['problem_id']}
- Title: {problem_info['title']}
- Language: {problem_info['language']}

Input Constraints:
{problem_info['constraints']}
{solution_code_section}
Task:
Write a Python function that generates diverse test case inputs that match the EXACT input format expected by the solution code.

CRITICAL INPUT FORMAT REQUIREMENTS:
1. If the solution code reads multiple test cases (has `int t` followed by a loop):
   - The generator must return a list of `n` COMPLETE input strings
   - Each string should be: "<t>\\n<case1>\\n<case2>\\n...\\n<case_t>"
   - The value of t should vary based on test case distribution:
     * SMALL: t = 1-5 test cases per input, each case with small data
     * MEDIUM: t = 5-50 test cases per input, each case with medium data
     * LARGE: t can be large BUT each individual case must be smaller to keep total data reasonable
       - Example: If t = 1000, then each case should have small n (e.g., n ≤ 1000)
       - Example: If t = 10, then each case can have large n (e.g., n ≤ 100000)
       - RULE: Keep total data size reasonable (total elements across all cases ≤ 10^6)
   - Example: If generating 10 inputs, return 10 strings, each containing multiple test cases

2. If the solution code processes a single test case (no t variable):
   - The generator must return a list of `n` input strings
   - Each string is ONE test case: "<input_data>"
   - LARGE cases can use full maximum constraints since there's only one case per input

Test Case Distribution (STRICTLY ENFORCED):
- 50% should be SMALL inputs:
  * Edge cases: minimum values (0, 1, -1 where applicable)
  * Boundary conditions
  * Simple cases for manual verification

- 30% should be MEDIUM inputs:
  * Moderate size values (around 10-30% of maximum constraint)
  * Typical use cases

- 20% should be LARGE inputs (CRITICAL - MUST INCLUDE):
  * Use MAXIMUM or NEAR-MAXIMUM values from the constraints
  * Example: If constraint is "1 ≤ n ≤ 10^5", use n = 100000 or n = 99999
  * Example: If constraint is "1 ≤ a[i] ≤ 10^9", use values like 10^9, 999999999
  * Test performance at scale
  * Stress test the algorithm
  * MANDATORY: At least 20% of test cases MUST use maximum constraint values

IMPORTANT REQUIREMENTS:
- Create a function named `generate_test_cases(n)` that takes the number of cases as parameter
- Returns a list of exactly `n` input strings
- Only use Python standard library (random, math, string, etc.)
- NO external dependencies (no numpy, no external packages)
- Each input string should be ready to be passed directly to stdin
- For multi-line inputs, use newline character (\\n)
- Include edge cases: minimum values, maximum values, boundary conditions
- STRICTLY follow the 50/30/20 distribution for small/medium/large cases
- For LARGE cases: Extract maximum values from constraints and USE THEM
- Match the EXACT input format from the solution code

CRITICAL: Return ONLY executable Python code. Do NOT include:
- Markdown code blocks (```python or ```)
- Explanations before or after the code
- Comments explaining what the code does
- Any text that is not valid Python syntax
- Placeholder code like case_data = "..." or case_data = '...'

IMPORTANT: You MUST write the COMPLETE implementation. Do NOT use placeholders like "..." or "# TODO" or "# Your logic here".
Every line of code must be fully implemented and ready to execute.

You must return ONLY the function definition starting with "def generate_test_cases(n):" and nothing else.

Example for MULTI-TEST CASE format (if solution has `int t` loop):
'''
Suppose the problem requires:
- Input: First line has t (number of test cases). Each test case has n (array size) and an array of n integers.
- Constraints: 1 <= t <= 1000, 1 <= n <= 10^5, 1 <= a[i] <= 10^9

Then your generator should look like:
'''
def generate_test_cases(n):
    import random
    test_cases = []

    # Calculate distribution: 50% small, 30% medium, 20% large
    num_small = n // 2
    num_medium = (n * 3) // 10
    num_large = n - num_small - num_medium

    # SMALL cases (50%)
    for _ in range(num_small):
        t = random.randint(1, 3)  # Few test cases
        cases = []
        for _ in range(t):
            arr_size = random.randint(1, 10)  # Small array
            arr = [random.randint(1, 100) for _ in range(arr_size)]
            cases.append(f"{{arr_size}}\\n{{' '.join(map(str, arr))}}")
        test_cases.append(f"{{t}}\\n{{chr(10).join(cases)}}")

    # MEDIUM cases (30%)
    for _ in range(num_medium):
        t = random.randint(5, 50)  # Moderate number of test cases
        cases = []
        for _ in range(t):
            arr_size = random.randint(100, 1000)  # Medium array
            arr = [random.randint(1, 10**6) for _ in range(arr_size)]
            cases.append(f"{{arr_size}}\\n{{' '.join(map(str, arr))}}")
        test_cases.append(f"{{t}}\\n{{chr(10).join(cases)}}")

    # LARGE cases (20%) - USE MAXIMUM CONSTRAINT VALUES
    for _ in range(num_large):
        # Use MAXIMUM t value from constraints
        t = random.randint(800, 1000)  # t <= 1000, so use close to max
        cases = []
        for _ in range(t):
            # Use MAXIMUM n and a[i] values
            arr_size = random.randint(90000, 100000)  # n <= 10^5
            arr = [random.randint(10**8, 10**9) for _ in range(arr_size)]  # a[i] <= 10^9
            cases.append(f"{{arr_size}}\\n{{' '.join(map(str, arr))}}")
        test_cases.append(f"{{t}}\\n{{chr(10).join(cases)}}")

    random.shuffle(test_cases)
    return test_cases

Now write the COMPLETE function based on the solution code format and constraints:"""

        try:
            response = self.model.generate_content(prompt)
            code = response.text.strip()

            # Remove markdown code blocks if present
            code = code.replace('```python\n', '').replace('```python', '')
            code = code.replace('```\n', '').replace('```', '')
            code = code.strip()

            # Extract only Python code (from first 'def' to end, removing any text before)
            import re
            import logging
            logger = logging.getLogger(__name__)

            # Find the start of the function definition
            def_match = re.search(r'^\s*def generate_test_cases', code, re.MULTILINE)
            if def_match:
                # Extract from 'def' onwards
                code = code[def_match.start():]
            else:
                logger.warning('Could not find "def generate_test_cases" in response')
                raise ValueError('Generated code does not contain generate_test_cases function')

            # Remove any explanatory text after the function
            # Look for common patterns that indicate end of code
            # Split by double newlines and take only valid Python code sections
            lines = code.split('\n')
            cleaned_lines = []
            in_function = False
            base_indent = None

            for line in lines:
                stripped = line.strip()

                # Start of function
                if stripped.startswith('def generate_test_cases'):
                    in_function = True
                    base_indent = len(line) - len(line.lstrip())
                    cleaned_lines.append(line)
                    continue

                if in_function:
                    # Empty line is ok
                    if not stripped:
                        cleaned_lines.append(line)
                        continue

                    # Check if line is part of function (indented or comment)
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent > base_indent or stripped.startswith('#'):
                        cleaned_lines.append(line)
                    else:
                        # Line with no indent or same as 'def' - likely end of function or explanatory text
                        if stripped and not stripped.startswith('#'):
                            # This looks like explanatory text, stop here
                            break
                        cleaned_lines.append(line)

            code = '\n'.join(cleaned_lines).strip()

            # Basic validation
            if 'def generate_test_cases' not in code:
                raise ValueError('Generated code does not contain generate_test_cases function')

            if 'return' not in code:
                raise ValueError('Generated function does not have a return statement')

            logger.info(f'Successfully extracted Python code ({len(code)} chars)')
            return code

        except Exception as e:
            raise ValueError(f'Failed to generate test case generator code: {str(e)}')

    def _validate_solution_with_samples(self, solution_code, samples):
        """
        Validate C++ solution code against sample test cases

        Args:
            solution_code: C++ code string
            samples: List of dicts with 'input' and 'output' keys

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        import tempfile
        import subprocess
        import os

        try:
            # Create temp directory for compilation
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = os.path.join(tmpdir, 'solution.cpp')
                binary_file = os.path.join(tmpdir, 'solution')

                # Write C++ code to file
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(solution_code)

                # Compile C++ code
                compile_cmd = [
                    'g++',
                    '-std=c++17',
                    '-O2',
                    '-Wall',
                    source_file,
                    '-o',
                    binary_file
                ]

                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if compile_result.returncode != 0:
                    return False, f"Compilation error: {compile_result.stderr}"

                # Test each sample
                for idx, sample in enumerate(samples, 1):
                    sample_input = sample.get('input', '').strip()
                    expected_output = sample.get('output', '').strip()

                    # Run the binary with sample input
                    try:
                        run_result = subprocess.run(
                            [binary_file],
                            input=sample_input,
                            capture_output=True,
                            text=True,
                            timeout=2
                        )

                        if run_result.returncode != 0:
                            return False, f"Sample {idx} runtime error: {run_result.stderr}"

                        actual_output = run_result.stdout.strip()

                        # Compare outputs (normalize whitespace)
                        actual_lines = [line.strip() for line in actual_output.split('\n') if line.strip()]
                        expected_lines = [line.strip() for line in expected_output.split('\n') if line.strip()]

                        if actual_lines != expected_lines:
                            return False, f"Sample {idx} failed:\nInput: {sample_input}\nExpected: {expected_output}\nGot: {actual_output}"

                    except subprocess.TimeoutExpired:
                        return False, f"Sample {idx} timeout (>2s)"

                # All samples passed
                return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def extract_problem_info_from_url(self, problem_url, progress_callback=None, additional_context=None):
        """
        Extract problem information from URL using Gemini AI

        Args:
            problem_url: URL of the problem page
            progress_callback: Optional function to call with progress updates
            additional_context: Optional additional context (e.g., counterexamples, edge cases)
                               to provide to AI for better solution generation

        Returns:
            dict: {
                'title': str,
                'constraints': str,
                'solution_code': str (C++ code)
            }

        Raises:
            ValueError: If API key not configured or extraction fails
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        def update_progress(message):
            """Helper to update progress if callback provided"""
            if progress_callback:
                progress_callback(message)

        try:
            import time
            import random

            # Random User-Agent pool to avoid pattern detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            # Random Accept-Language values
            accept_languages = [
                'en-US,en;q=0.9',
                'en-US,en;q=0.9,ko;q=0.8',
                'en-GB,en;q=0.9',
                'en-US,en;q=0.8',
            ]

            # Fetch the webpage content with randomized headers to avoid bot detection
            # Note: Don't set Accept-Encoding - let requests handle it automatically
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': random.choice(accept_languages),
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
            }

            # Add random delay to avoid rate limiting (3-7 seconds)
            time.sleep(random.uniform(3, 7))

            # Use session to maintain cookies
            session = requests.Session()
            session.headers.update(headers)

            # Try to get the page with retry logic
            max_retries = 3
            update_progress("Fetching webpage...")
            for attempt in range(max_retries):
                try:
                    response = session.get(problem_url, timeout=30, allow_redirects=True)

                    if response.status_code == 403:
                        if attempt < max_retries - 1:
                            update_progress(f"Retrying fetch (attempt {attempt + 2}/{max_retries})...")
                            # Wait longer on retry with exponential backoff
                            wait_time = random.uniform(5, 10) * (attempt + 1)
                            time.sleep(wait_time)

                            # Change User-Agent for retry
                            session.headers['User-Agent'] = random.choice(user_agents)
                            continue
                        else:
                            raise ValueError(f'Failed to fetch problem URL after {max_retries} attempts: 403 Forbidden. The website may be blocking automated requests.')

                    response.raise_for_status()

                    # Let requests handle decompression automatically
                    # It will decompress gzip/deflate/br if needed
                    import logging
                    logger = logging.getLogger(__name__)

                    # Use response.text which handles encoding automatically
                    raw_html = response.text

                    # Log raw HTML for debugging
                    logger.info(f"Raw HTML fetched from {problem_url}")
                    logger.info(f"HTML length: {len(raw_html)} characters")
                    logger.info(f"HTML preview (first 2000 chars):\n{raw_html[:2000]}")
                    logger.info(f"HTML status code: {response.status_code}")
                    logger.info(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    logger.info(f"Response encoding: {response.encoding}")

                    webpage_content = raw_html
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        update_progress(f"Retrying fetch (attempt {attempt + 2}/{max_retries})...")
                        wait_time = random.uniform(3, 6) * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f'Failed to fetch problem URL: {str(e)}')

            # Extract clean text from HTML using BeautifulSoup
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(webpage_content, 'html.parser')

            # Platform-specific HTML parsing to extract only problem content
            update_progress("Extracting problem content...")
            problem_content = None

            # Codeforces: Extract problem statement div
            if 'codeforces.com' in problem_url:
                # Try to find problem statement div
                problem_div = soup.find('div', class_='problem-statement')
                if problem_div:
                    logger.info("Found Codeforces problem-statement div")
                    problem_content = problem_div
                else:
                    logger.warning("Could not find problem-statement div, using full content")

            # Baekjoon: Extract problem content
            elif 'acmicpc.net' in problem_url:
                problem_div = soup.find('div', id='problem-body') or soup.find('div', id='problem_description')
                if problem_div:
                    logger.info("Found Baekjoon problem content div")
                    problem_content = problem_div
                else:
                    logger.warning("Could not find problem body div, using full content")

            # Use extracted content or fall back to full soup
            if problem_content:
                soup = BeautifulSoup(str(problem_content), 'html.parser')
                logger.info(f"Using extracted problem content (HTML length: {len(str(problem_content))} chars)")

            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            # Get text and clean it up - use separator to ensure spacing between elements
            text = soup.get_text(separator=' ', strip=True)

            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)

            # Clean up multiple spaces
            import re
            webpage_content = re.sub(r' +', ' ', webpage_content)

            # Log parsed content for debugging
            logger.info(f"Parsed webpage content length: {len(webpage_content)} characters")
            logger.info(f"Parsed content preview (first 2000 chars):\n{webpage_content[:2000]}")

            # Limit content size to avoid token limits (increased to 80000 since we're filtering)
            if len(webpage_content) > 80000:
                logger.info(f"Content truncated from {len(webpage_content)} to 80000 characters")
                webpage_content = webpage_content[:80000]

            # Try up to 3 times to generate and validate a correct solution
            max_attempts = 3
            last_error = None

            update_progress("Analyzing problem...")

            for attempt in range(1, max_attempts + 1):
                import logging
                logger = logging.getLogger(__name__)

                if attempt == 1:
                    update_progress("Generating solution (AI thinking)...")
                else:
                    update_progress(f"Regenerating solution (attempt {attempt}/{max_attempts})...")
                    logger.info(f"Retry attempt {attempt}/{max_attempts} to generate correct solution...")

                # Build additional context section if provided
                additional_context_section = ""
                if additional_context:
                    additional_context_section = f"""

ADDITIONAL CONTEXT FROM ADMIN:
The previous solution had issues. Please consider this feedback when generating the new solution:
{additional_context}

IMPORTANT: Analyze this feedback carefully and ensure your new solution addresses these specific issues.
"""

                prompt = f"""You are a TOP-RANKED competitive programming expert with multiple years of experience solving Codeforces, Baekjoon, and ICPC problems.

Your task is to analyze the following problem webpage and extract:
1. Problem title
2. Input/output constraints (detailed format, limits, and rules)
3. Sample input(s) and expected output(s) from the problem statement
4. A CORRECT, OPTIMIZED C++ solution

CRITICAL REQUIREMENTS FOR THE C++ SOLUTION:
- YOU ARE A COMPETITIVE PROGRAMMING EXPERT - write code that you would submit in a real contest
- The solution MUST be ALGORITHMICALLY CORRECT first, then optimized
- Carefully analyze the problem logic, edge cases, and corner cases
- Think through the algorithm step-by-step before writing code
- The solution MUST pass ALL test cases, including edge cases
- Use correct data types (long long for large numbers, avoid integer overflow)
- Handle special cases: n=0, n=1, negative numbers, empty input, maximum constraints
- Use efficient algorithms: O(n log n) or better when possible
- Use fast I/O: ios_base::sync_with_stdio(false), cin.tie(NULL), cout.tie(NULL)
- Avoid TLE: no unnecessary operations, optimize loops, use appropriate data structures
- NO EXPLANATIONS, NO COMMENTS in the code - only pure working C++ code

SAMPLE INPUT/OUTPUT EXTRACTION:
- Extract ALL sample inputs and outputs from the problem statement
- Format each sample as: "input" and "output" pairs
- If there are multiple samples, include all of them
- These will be used to verify your solution is correct
{additional_context_section}
CRITICAL: You MUST return ONLY a valid JSON object. Do NOT include any text before or after the JSON.

Return your response in EXACTLY this format:
{{
    "title": "problem title here",
    "constraints": "detailed input/output format, constraints, and limits",
    "samples": [
        {{"input": "sample input 1", "output": "expected output 1"}},
        {{"input": "sample input 2", "output": "expected output 2"}}
    ],
    "solution_code": "<COMPLETE C++ CODE WITH #include, main(), FAST I/O, AND FULL IMPLEMENTATION>"
}}

Webpage content:
{webpage_content}

Remember:
1. You are a competitive programming EXPERT - write code that WORKS
2. Think carefully about the algorithm and edge cases
3. Return ONLY the JSON object. No markdown, no explanations.{' IMPORTANT: This is attempt ' + str(attempt) + ' of ' + str(max_attempts) + '. The solution MUST be correct.' if attempt > 1 else ''}"""

                # Log the full prompt being sent to Gemini
                logger.info("="*80)
                logger.info(f"GEMINI PROMPT (Attempt {attempt}/{max_attempts}):")
                logger.info("="*80)
                logger.info(prompt)
                logger.info("="*80)

                try:
                    # Generate response
                    response = self.model.generate_content(prompt)
                    response_text = response.text.strip()

                    # Log the Gemini response
                    logger.info("="*80)
                    logger.info(f"GEMINI RESPONSE (Attempt {attempt}/{max_attempts}):")
                    logger.info("="*80)
                    logger.info(response_text)
                    logger.info("="*80)

                    # Check if Gemini returned an error about corrupted content
                    if 'corrupted' in response_text.lower() or 'garbled' in response_text.lower() or 'unsupported encoding' in response_text.lower():
                        logger.error("Gemini reported corrupted/garbled content")
                        logger.error(f"Gemini response: {response_text}")
                        logger.error(f"Full webpage content sent to Gemini ({len(webpage_content)} chars):\n{webpage_content}")
                        raise ValueError(f"Gemini could not parse webpage: {response_text}")

                    # Remove markdown code blocks if present
                    response_text = response_text.replace('```json\n', '').replace('```json', '')
                    response_text = response_text.replace('```\n', '').replace('```', '')
                    response_text = response_text.strip()

                    # Parse JSON response with better error handling
                    import re

                    try:
                        # First try to extract JSON from markdown code block
                        json_block_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
                        if json_block_match:
                            json_str = json_block_match.group(1).strip()
                            logger.info('Found JSON in markdown code block')
                        else:
                            # Try direct parsing
                            json_str = response_text.strip()

                        result = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.warning(f'JSON parse failed: {e}. Attempting to extract JSON object.')

                        # Try to find JSON object by matching balanced braces
                        first_brace = response_text.find('{')
                        if first_brace == -1:
                            logger.error(f'No opening brace found. Response text (first 500 chars): {response_text[:500]}')
                            raise ValueError('No JSON object found in Gemini response')

                        # Find matching closing brace
                        brace_count = 0
                        in_string = False
                        escape_next = False
                        last_brace = -1

                        for i in range(first_brace, len(response_text)):
                            char = response_text[i]

                            if escape_next:
                                escape_next = False
                                continue

                            if char == '\\':
                                escape_next = True
                                continue

                            if char == '"':
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        last_brace = i
                                        break

                        if last_brace == -1:
                            logger.error(f'No matching closing brace found. Response text (first 500 chars): {response_text[:500]}')
                            raise ValueError('Incomplete JSON object in Gemini response')

                        json_str = response_text[first_brace:last_brace + 1]
                        try:
                            result = json.loads(json_str)
                            logger.info('Successfully extracted JSON from response using brace matching')
                        except json.JSONDecodeError as e2:
                            logger.error(f'Failed to parse extracted JSON: {e2}')
                            logger.error(f'Extracted JSON (first 500 chars): {json_str[:500]}')
                            raise ValueError(f'Failed to parse JSON from Gemini response: {str(e2)}')

                    # Validate required fields
                    required_fields = ['title', 'constraints', 'solution_code']
                    if not all(key in result for key in required_fields):
                        missing_fields = [key for key in required_fields if key not in result]
                        logger.error(f'Missing required fields: {missing_fields}')
                        logger.error(f'Received keys: {list(result.keys())}')
                        raise ValueError(f'Missing required fields in Gemini response: {missing_fields}')

                    # Check if solution_code is a placeholder and extract actual code from response
                    solution_code = result.get('solution_code', '')
                    if 'MUST be correct' in solution_code or 'code here' in solution_code.lower() or 'placeholder' in solution_code.lower() or len(solution_code) < 100:
                        logger.warning('solution_code appears to be a placeholder. Extracting code from response.')

                        # Try multiple extraction methods
                        actual_code = None

                        # Method 1: Find C++ code block (```cpp ... ```)
                        cpp_match = re.search(r'```cpp\s*\n(.*?)\n```', response_text, re.DOTALL)
                        if cpp_match:
                            actual_code = cpp_match.group(1).strip()
                            logger.info(f'Method 1: Extracted C++ from code block ({len(actual_code)} chars)')

                        # Method 2: Find code block without language specifier (``` ... ```) after JSON
                        if not actual_code or len(actual_code) < 100:
                            # Find JSON closing brace, then look for code block after it
                            json_end = response_text.rfind('}')
                            if json_end != -1:
                                after_json = response_text[json_end:]
                                code_block_match = re.search(r'```\s*\n(#include.*?)\n```', after_json, re.DOTALL)
                                if code_block_match:
                                    actual_code = code_block_match.group(1).strip()
                                    logger.info(f'Method 2: Extracted from code block after JSON ({len(actual_code)} chars)')

                        # Method 3: Find complete C++ code from #include to return 0;
                        if not actual_code or len(actual_code) < 100:
                            # Look for #include ... int main() ... return 0;
                            cpp_pattern = r'(#include[\s\S]*?int\s+main\s*\([^\)]*\)[\s\S]*?return\s+0\s*;[\s\S]*?\})'
                            include_match = re.search(cpp_pattern, response_text)
                            if include_match:
                                actual_code = include_match.group(1).strip()
                                logger.info(f'Method 3: Extracted from #include to return 0 ({len(actual_code)} chars)')

                        # Method 4: Find any code starting with #include
                        if not actual_code or len(actual_code) < 100:
                            # Find from #include to end, but stop at markdown or JSON
                            parts = response_text.split('#include')
                            if len(parts) > 1:
                                code_part = '#include' + parts[-1]
                                # Clean up: stop at next ``` or {
                                clean_end = min(
                                    [len(code_part)] +
                                    [code_part.find('```', 1) if code_part.find('```', 1) != -1 else len(code_part)] +
                                    [code_part.find('\n{', 1) if code_part.find('\n{', 1) != -1 else len(code_part)]
                                )
                                actual_code = code_part[:clean_end].strip()
                                logger.info(f'Method 4: Extracted from #include to end ({len(actual_code)} chars)')

                        if actual_code and len(actual_code) >= 100:
                            result['solution_code'] = actual_code
                            logger.info(f'Successfully extracted C++ code: {len(actual_code)} characters')
                        else:
                            logger.error('Could not extract valid C++ code from response')
                            logger.error(f'Response preview: {response_text[:1000]}')

                    # Get samples if available
                    samples = result.get('samples', [])

                    # If samples are provided, validate the solution against them
                    if samples and len(samples) > 0:
                        logger.info(f'Found {len(samples)} sample test cases. Validating solution...')
                        update_progress(f"Testing solution ({len(samples)} sample{'s' if len(samples) > 1 else ''})...")

                        validation_passed, validation_error = self._validate_solution_with_samples(
                            result['solution_code'],
                            samples
                        )

                        if not validation_passed:
                            logger.warning(f'Attempt {attempt}/{max_attempts} - Solution failed sample validation: {validation_error}')

                            # If this is not the last attempt, retry
                            if attempt < max_attempts:
                                last_error = validation_error
                                update_progress(f"Sample test failed, retrying...")
                                continue
                            else:
                                # On last attempt, save the result with warning instead of failing completely
                                logger.warning(f'⚠ Solution failed validation after {max_attempts} attempts, but saving anyway')
                                result['validation_warning'] = f'Solution may be incorrect: {validation_error}'
                                result['validation_passed'] = False
                                update_progress(f"⚠ Solution saved with validation warning")
                                return result

                        logger.info(f'✓ Solution passed all {len(samples)} sample test cases on attempt {attempt}')
                        result['validation_passed'] = True
                        update_progress(f"✓ Solution verified with {len(samples)} samples")
                    else:
                        logger.warning('No sample test cases provided for validation')

                    # Success!
                    return result

                except ValueError as e:
                    # Validation or parsing error - retry if not last attempt
                    if attempt < max_attempts and 'failed sample test cases' in str(e):
                        last_error = str(e)
                        continue
                    else:
                        raise

            # If we get here, all attempts failed
            if last_error:
                raise ValueError(f'Failed to generate correct solution after {max_attempts} attempts. Last error: {last_error}')
            else:
                raise ValueError(f'Failed to generate solution after {max_attempts} attempts')

        except requests.RequestException as e:
            raise ValueError(f'Failed to fetch problem URL: {str(e)}')
        except Exception as e:
            raise ValueError(f'Failed to extract problem info: {str(e)}')

    def generate_hints(self, user_code, solution_code, test_failures, problem_info):
        """
        Generate progressive hints based on user's failed code

        Args:
            user_code: str - User's incorrect code
            solution_code: str - The correct solution code
            test_failures: list - List of failed test case results with inputs/outputs
            problem_info: dict - Problem information (title, constraints, etc.)

        Returns:
            list: 3-5 progressive hints ordered from general to specific

        Raises:
            ValueError: If API key not configured or generation fails
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        # Prepare test failure summary and detect error types
        failure_summary = []
        has_syntax_error = False
        has_runtime_error = False
        has_segfault = False

        for idx, failure in enumerate(test_failures[:3], 1):  # Limit to 3 examples
            error = failure.get('error', 'None')

            # Detect error types
            if error and error != 'None':
                error_lower = error.lower()
                if 'syntax' in error_lower or 'parse' in error_lower or 'invalid syntax' in error_lower:
                    has_syntax_error = True
                if 'segmentation fault' in error_lower or 'sigsegv' in error_lower:
                    has_segfault = True
                if 'runtime error' in error_lower or 'exception' in error_lower:
                    has_runtime_error = True

            failure_summary.append(
                f"Test Case {idx}:\n"
                f"  Input: {failure.get('input', 'N/A')}\n"
                f"  Expected: {failure.get('expected', 'N/A')}\n"
                f"  Your Output: {failure.get('output', 'N/A')}\n"
                f"  Error: {error}"
            )

        failures_text = '\n\n'.join(failure_summary)

        # Determine error context for hints
        error_context = ""
        if has_syntax_error:
            error_context = "Note: The code has syntax errors. Focus hints on fixing syntax issues first."
        elif has_segfault:
            error_context = "Note: The code causes segmentation faults. Focus hints on memory access issues, array bounds, null pointers, or stack overflow."
        elif has_runtime_error:
            error_context = "Note: The code has runtime errors. Focus hints on logic errors, edge cases, and algorithm correctness."
        else:
            error_context = "Note: The code compiles but produces incorrect output. Focus hints on logic errors and algorithm correctness. DO NOT mention syntax or compilation issues."

        prompt = f"""You are an expert programming tutor helping a student debug their code.

Problem Information:
- Title: {problem_info.get('title', 'N/A')}
- Platform: {problem_info.get('platform', 'N/A')}
- Problem ID: {problem_info.get('problem_id', 'N/A')}
- Language: {problem_info.get('language', 'N/A')}

Student's Code (INCORRECT):
```
{user_code}
```

Failed Test Cases:
{failures_text}

Reference Solution (DO NOT REVEAL THIS DIRECTLY):
```
{solution_code}
```

{error_context}

Task:
Generate 3-5 progressive hints to help the student fix their code. The hints should:

1. Start with general debugging approaches (e.g., "Check edge cases", "Review your logic for...")
2. Gradually become more specific (e.g., "Look at how you handle...", "Consider the data type of...")
3. Guide toward the solution WITHOUT giving away the exact answer
4. Be encouraging and educational
5. Each hint should be a single, clear statement (1-2 sentences max)
6. Never reveal the solution code directly
7. Focus on the specific errors shown in the test cases
8. IMPORTANT: Each hint must be UNIQUE and DISTINCT - do NOT repeat the same advice in different words
9. IMPORTANT: If there are no syntax or compilation errors, DO NOT mention syntax, compilation, or parsing issues at all
10. Provide hints that progressively guide the student from identifying the problem to understanding how to fix it

CRITICAL: Return ONLY a valid JSON array of hint strings. Do NOT include:
- Any text before or after the JSON array
- Markdown code blocks (```json or ```)
- Explanations or comments
- Any formatting except the JSON array
- Duplicate or repetitive hints

Example format (replace with your actual hints):
[
    "Start by checking if your code handles edge cases like empty input or single elements.",
    "Look carefully at how you're processing the input - are you reading all the values correctly?",
    "Consider the data type of your variables - integers vs strings can cause unexpected behavior.",
    "Review your loop logic - are you iterating through all elements or missing some?",
    "The issue might be in how you're formatting the output - check for extra spaces or newlines."
]

Now generate the hints:"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            response_text = response_text.replace('```json\n', '').replace('```json', '')
            response_text = response_text.replace('```\n', '').replace('```', '')
            response_text = response_text.strip()

            # Parse JSON response
            import re
            import logging
            logger = logging.getLogger(__name__)

            try:
                # First try direct parsing
                hints = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f'Direct JSON parse failed: {e}. Attempting to extract JSON from response.')

                # Try to find JSON array in the response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    try:
                        hints = json.loads(json_str)
                        logger.info('Successfully extracted JSON array from response')
                    except json.JSONDecodeError as e2:
                        logger.error(f'Failed to parse extracted JSON: {e2}')
                        raise ValueError(f'Failed to parse JSON from Gemini response: {str(e2)}')
                else:
                    logger.error(f'No JSON array found in response. Response text: {response_text[:500]}')
                    raise ValueError('No JSON array found in Gemini response')

            # Validate that we got a list
            if not isinstance(hints, list):
                raise ValueError('Gemini response is not a JSON array')

            # Validate that we have 3-5 hints
            if len(hints) < 3:
                logger.warning(f'Only {len(hints)} hints generated, expected at least 3')
            elif len(hints) > 5:
                logger.warning(f'{len(hints)} hints generated, truncating to 5')
                hints = hints[:5]

            # Validate that all hints are strings
            if not all(isinstance(hint, str) for hint in hints):
                raise ValueError('Not all hints are strings')

            logger.info(f'Successfully generated {len(hints)} hints')
            return hints

        except Exception as e:
            raise ValueError(f'Failed to generate hints: {str(e)}')

    def extract_problem_metadata_from_url(self, problem_url, difficulty_rating=None, progress_callback=None):
        """
        Step 1: Extract only problem metadata (title, constraints, samples) from URL
        This is separated from solution generation to allow Gemini to focus on extraction first.

        Args:
            problem_url: URL to the problem page
            difficulty_rating: Optional difficulty rating (e.g., 2500 for Codeforces)
            progress_callback: Optional callback function to report progress

        Returns:
            dict: {
                'title': str,
                'constraints': str,
                'samples': list of {'input': str, 'output': str},
                'platform': str,
                'problem_id': str
            }
        """
        import logging
        import re

        logger = logging.getLogger(__name__)

        if not self.model:
            raise ValueError('Gemini API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        try:
            # Fetch webpage content
            update_progress("Fetching webpage...")
            import time
            import random
            from bs4 import BeautifulSoup

            # Random User-Agent pool to avoid pattern detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            # Random Accept-Language values
            accept_languages = [
                'en-US,en;q=0.9',
                'en-US,en;q=0.9,ko;q=0.8',
                'en-GB,en;q=0.9',
                'en-US,en;q=0.8',
            ]

            # Fetch with randomized headers to avoid bot detection
            # Don't set Accept-Encoding - let requests handle it automatically
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': random.choice(accept_languages),
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
            }

            # Add random delay to avoid rate limiting (3-7 seconds)
            time.sleep(random.uniform(3, 7))

            # Use session to maintain cookies
            session = requests.Session()
            session.headers.update(headers)

            # Try to get the page with retry logic
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = session.get(problem_url, timeout=30, allow_redirects=True)

                    if response.status_code == 403:
                        if attempt < max_retries - 1:
                            update_progress(f"Retrying fetch (attempt {attempt + 2}/{max_retries})...")
                            # Wait longer on retry with exponential backoff
                            wait_time = random.uniform(5, 10) * (attempt + 1)
                            time.sleep(wait_time)

                            # Change User-Agent for retry
                            session.headers['User-Agent'] = random.choice(user_agents)
                            continue
                        else:
                            raise ValueError(f'Failed to fetch problem URL after {max_retries} attempts: 403 Forbidden. The website may be blocking automated requests.')

                    response.raise_for_status()
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        update_progress(f"Retrying fetch (attempt {attempt + 2}/{max_retries})...")
                        wait_time = random.uniform(3, 6) * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f'Failed to fetch problem URL: {str(e)}')

            # Extract clean text from HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Platform-specific HTML parsing to extract only problem content
            update_progress("Extracting problem content...")
            problem_content = None

            # Codeforces: Extract problem statement div
            if 'codeforces.com' in problem_url:
                # Try to find problem statement div
                problem_div = soup.find('div', class_='problem-statement')
                if problem_div:
                    logger.info("Found Codeforces problem-statement div")
                    problem_content = problem_div
                else:
                    logger.warning("Could not find problem-statement div, using full content")

            # Baekjoon: Extract problem content
            elif 'acmicpc.net' in problem_url:
                problem_div = soup.find('div', id='problem-body') or soup.find('div', id='problem_description')
                if problem_div:
                    logger.info("Found Baekjoon problem content div")
                    problem_content = problem_div
                else:
                    logger.warning("Could not find problem body div, using full content")

            # Use extracted content or fall back to full soup
            if problem_content:
                soup = BeautifulSoup(str(problem_content), 'html.parser')
                logger.info(f"Using extracted problem content (HTML length: {len(str(problem_content))} chars)")

            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            # Get text and clean it up - use separator to ensure spacing between elements
            text = soup.get_text(separator=' ', strip=True)

            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)

            # Clean up multiple spaces
            import re
            webpage_content = re.sub(r' +', ' ', webpage_content)

            # Log parsed content for debugging
            logger.info(f"Parsed webpage content length: {len(webpage_content)} characters")
            logger.info(f"Parsed content preview (first 2000 chars):\n{webpage_content[:2000]}")

            # Limit content size to avoid token limits (increased to 80000 since we're filtering)
            if len(webpage_content) > 80000:
                logger.info(f"Content truncated from {len(webpage_content)} to 80000 characters")
                webpage_content = webpage_content[:80000]

            # Log webpage content info
            logger.info(f"Fetched webpage: {len(response.text)} HTML chars, converted to {len(webpage_content)} plain text chars")
            logger.debug(f"Plain text preview (first 1000 chars): {webpage_content[:1000]}")

            # Check if webpage contains basic problem indicators
            has_title_indicators = any(keyword in webpage_content.lower() for keyword in ['problem', 'title', 'input', 'output', 'constraint', 'sample', 'example'])
            logger.info(f"Webpage has problem indicators: {has_title_indicators}")

            # Build difficulty-specific warning
            difficulty_warning = ""
            if difficulty_rating and difficulty_rating >= 2500:
                difficulty_warning = f"""
⚠️ IMPORTANT: This problem has a difficulty rating of {difficulty_rating} (Expert level).
Pay extra attention to:
- Complex constraint patterns (multiple variables with dependencies)
- Non-obvious input formats (graphs, trees, special structures)
- Large constraint values (10^5, 10^6, 10^9) - extract EXACT limits
- Multiple test case formats (T test cases vs. single case)
"""

            # Prompt focused ONLY on extraction with difficulty awareness
            prompt = f"""You are a competitive programming problem parser specializing in Codeforces, Baekjoon, ICPC, and IOI problems.

## YOUR TASK
Extract the problem metadata in structured JSON format. DO NOT solve the problem or generate code.

{difficulty_warning}

## EXTRACTION REQUIREMENTS

### 1. Title
- Extract the EXACT problem title as displayed on the page

### 2. Constraints (INPUT FORMAT ONLY)
You must extract with PRECISE detail:
- First line format: "First line contains..."
- Subsequent line formats: "Next N lines contain..."
- Variable ranges with correct notation: "1 ≤ N ≤ 10^5" or "1 ≤ N ≤ 100000"
- Multi-test case format: "First line contains T (number of test cases)"
- Array/sequence formats: "Next line contains N space-separated integers"
- String constraints: "String length ≤ 10^6, contains only lowercase letters"
- Graph formats: "Next M lines contain edges (u, v)"

DO NOT include:
- Output format descriptions
- Time/memory limits
- Problem descriptions or stories
- Solution approaches

### 3. Sample Test Cases - CRITICAL EXTRACTION RULES

⚠️ EXTREME PRECISION REQUIRED: These samples will be used for automated C++ solution validation via stdin/stdout comparison.

**Identification Patterns (Look for these labels/keywords):**
- **Input indicators**: "Input", "Sample Input", "예제 입력", "stdin", "Example Input", "Test Input", "입력"
- **Output indicators**: "Output", "Sample Output", "예제 출력", "stdout", "Example Output", "Test Output", "출력"
- **Separators**: Horizontal lines, blank lines, section headers between input/output

**Extraction Rules (STRICT):**
1. **Exact Character Extraction**:
   - Extract ONLY the data lines (no labels, no headers like "Input:", "Output:")
   - Each character, space, newline must be EXACTLY as shown in the problem
   - DO NOT add quotes, brackets, or any wrapper characters
   - DO NOT add or remove ANY whitespace, newlines, or blank lines
   - DO NOT interpret or format numbers (keep "0003" as "0003", not "3")

2. **Input/Output Boundaries**:
   - Input ends where output begins (typically at output label or separator)
   - If multiple samples exist, each has its own input/output pair
   - Number samples sequentially (Sample 1, Sample 2, etc.)

3. **Formatting Preservation**:
   - Single space between numbers → keep as single space
   - Multiple lines → preserve with \\n (newline character)
   - Trailing spaces → preserve them
   - Empty lines within sample → preserve them
   - Leading zeros → preserve them (e.g., "007" not "7")

4. **Common Mistakes to AVOID**:
   ❌ Including labels: "Input: 3\\n1 2 3" → ✓ Should be: "3\\n1 2 3"
   ❌ Changing newlines: "3 1 2 3" → ✓ Should be: "3\\n1 2 3" (if shown on separate lines)
   ❌ Adding spaces: "3\\n1 2 3" → ❌ "3 \\n 1 2 3"
   ❌ Removing trailing newlines in output
   ❌ Converting number formats: "00042" → ❌ "42"

5. **Multiple Samples**:
   - Extract ALL samples from the problem (typically 2-5 samples)
   - Keep them as separate entries in the samples array
   - DO NOT merge multiple samples into one

**Validation Format:**
Each sample must be ready for C++ stdin/stdout validation:
{{"input": "3\\n1 2 3", "output": "6"}}  // ONLY raw data, use \\n for newlines

**Platform-Specific Notes:**
- **Codeforces**: Samples in "Input/Output" sections under examples
- **Baekjoon (acmicpc.net)**: "예제 입력 1" / "예제 출력 1" with sequential numbering
- **LeetCode**: May show as function calls - extract equivalent stdin format
- **AtCoder**: "Sample Input 1" / "Sample Output 1"

**Quality Check Before Returning:**
- ✓ Did I remove ALL labels and headers?
- ✓ Are newlines represented as \\n (not actual line breaks in JSON)?
- ✓ Did I preserve exact spacing between numbers?
- ✓ Are multiple samples separated into distinct array entries?
- ✓ Would this exact string work as stdin for a C++ program?

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no code blocks):
{{
    "title": "Problem Title",
    "constraints": "First line: integer N (1 ≤ N ≤ 10^5)\\nNext N lines: each contains two integers A_i, B_i (1 ≤ A_i, B_i ≤ 10^9)",
    "samples": [
        {{"input": "3\\n1 2\\n3 4\\n5 6", "output": "6\\n12\\n30"}},
        {{"input": "1\\n100 200", "output": "20000"}}
    ]
}}

## WEBPAGE CONTENT
{webpage_content}

Return ONLY valid JSON, nothing else."""

            update_progress("Extracting problem metadata...")
            logger.info(f"Sending prompt to Gemini (webpage content: {len(webpage_content)} chars)")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            logger.info(f"Gemini response received: {len(response_text)} chars")
            logger.info(f"Gemini full response: {response_text}")  # Log full response to see what Gemini returns

            # Try multiple JSON extraction methods
            import json as json_module
            result = None

            # Method 1: Find JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_match:
                try:
                    result = json_module.loads(json_match.group(1))
                    logger.info("Extracted JSON from code block")
                except:
                    pass

            # Method 2: Find largest JSON object
            if not result:
                json_matches = re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
                largest_match = None
                max_length = 0
                for match in json_matches:
                    if len(match.group()) > max_length:
                        largest_match = match
                        max_length = len(match.group())

                if largest_match:
                    try:
                        result = json_module.loads(largest_match.group())
                        logger.info("Extracted JSON from largest object")
                    except:
                        pass

            # Method 3: Find any JSON-like structure
            if not result:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        result = json_module.loads(json_match.group())
                        logger.info("Extracted JSON with basic regex")
                    except:
                        pass

            if not result:
                logger.error(f"Failed to parse JSON. Full response: {response_text}")
                raise ValueError(f'No valid JSON found in response. Preview: {response_text[:200]}...')

            logger.info(f"Parsed JSON result: {result}")

            # Validate required fields
            if not result.get('title') or result.get('title').strip() == '':
                logger.error(f"Missing or empty title in extracted data. Full result: {result}")
                logger.error(f"Webpage content preview: {webpage_content[:1000]}")
                raise ValueError(f'Missing title in extracted data: {result}')
            if not result.get('constraints'):
                logger.warning('Missing constraints, using empty string')
                result['constraints'] = 'No constraints provided'

            # Parse problem URL
            platform, problem_id = self._parse_problem_url(problem_url)
            result['platform'] = platform
            result['problem_id'] = problem_id

            logger.info(f"Successfully extracted metadata: {result['title']}, {len(result.get('samples', []))} samples")
            return result

        except requests.RequestException as e:
            raise ValueError(f'Failed to fetch problem URL: {str(e)}')
        except Exception as e:
            logger.error(f"Error in extract_problem_metadata_from_url: {e}", exc_info=True)
            raise ValueError(f'Failed to extract problem metadata: {str(e)}')

    def generate_solution_for_problem(self, problem_metadata, difficulty_rating=None, previous_attempt=None, progress_callback=None):
        """
        Step 2: Generate solution code for the extracted problem
        This is separated to allow Gemini to focus entirely on solving the problem.

        Args:
            problem_metadata: dict with title, constraints, samples, platform, problem_id
            difficulty_rating: Optional difficulty rating (e.g., 2500 for Codeforces)
            previous_attempt: dict with 'code', 'error' if this is a retry
            progress_callback: Optional callback function to report progress

        Returns:
            dict: {
                'solution_code': str (C++ code),
                'attempt_number': int
            }
        """
        import logging
        import re

        logger = logging.getLogger(__name__)

        if not self.model:
            raise ValueError('Gemini API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        # Get difficulty-specific guidance and algorithm hints
        difficulty_guidance = self.get_difficulty_guidance(difficulty_rating)
        algorithm_hints = self.get_algorithm_hints(difficulty_rating)

        # Try to detect problem category and get few-shot examples
        few_shot_examples = ""
        if difficulty_rating and difficulty_rating >= 2500:
            try:
                category = self.analyze_problem_category(problem_metadata)
                if category:
                    few_shot_examples = self.get_few_shot_examples(category, difficulty_rating)
                    logger.info(f"Added few-shot examples for category: {category}")
            except Exception as e:
                logger.warning(f"Could not get few-shot examples: {e}")

        # Build retry context if this is not the first attempt
        retry_context = ""
        if previous_attempt:
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
   - Empty input (N=0)?
   - Single element (N=1)?
   - Maximum constraints?
   - Negative numbers or special values?
4. **Implementation Bugs**: Off-by-one errors? Integer overflow? Array bounds?

### Your Task Now:
Generate a CORRECTED solution that fixes the specific failure above.
"""

        # Build samples display
        samples_str = "\n".join([
            f"""Sample {i+1}:
Input:
{s['input']}

Expected Output:
{s['output']}
"""
            for i, s in enumerate(problem_metadata.get('samples', []))
        ])

        # Calculate expected complexity for constraints (NEW)
        constraints_hint = ""
        constraints_text = problem_metadata.get('constraints', '')
        # Try to extract N constraints
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

        prompt = f"""You are an ELITE competitive programmer (Grandmaster level) with expertise in solving Codeforces 2500+ problems, ICPC World Finals problems, and IOI problems.

Follow this EXACT protocol to solve the problem:

{difficulty_guidance}

## PROBLEM
**Title:** {problem_metadata['title']}

**Input Format and Constraints:**
{problem_metadata['constraints']}{constraints_hint}

**Sample Test Cases:**
{samples_str}

{algorithm_hints}

{few_shot_examples}

{retry_context}

═══════════════════════════════════════════════════════════════
## MANDATORY SOLUTION PROTOCOL
═══════════════════════════════════════════════════════════════

### Step 0: Problem Restatement (Comprehension Check)
Before solving, restate the problem in 2-3 lines to confirm understanding:
- What is the input format?
- What is the expected output?
- What is the core question being asked?

### Step 1: Problem Understanding & Analysis
Analyze what the problem is REALLY asking:
- What is the underlying problem pattern?
- Are there any implicit constraints or patterns?
- What problem category does this belong to? (DP, Graph, Greedy, Data Structure, Math, etc.)

### Step 2: Algorithm Selection with Complexity Proof
{f"Given the difficulty rating of {difficulty_rating}, consider:" if difficulty_rating and difficulty_rating >= 2500 else "Select the appropriate algorithm:"}
- What algorithm/data structure is needed?
- **Prove your complexity fits constraints:**
  - Calculate exact time complexity (e.g., O(N log N))
  - Verify it runs in < 1-2 seconds for max constraints
  - Show calculation: "N=10⁵, O(N log N) ≈ 10⁵ × 17 ≈ 1.7M ops ✓"
- Is there a well-known algorithm/pattern this matches?

### Step 3: Edge Case Analysis & Common Pitfalls

**Edge Cases to Test:**
- **Minimum values**: N=0, N=1, single element, empty array/string
- **Maximum values**: N=10⁵, values=10⁹, stress testing at limits
- **Special cases**: All elements equal, already sorted, reverse sorted, alternating patterns
- **Boundary conditions**: First/last elements, modulo arithmetic (10⁹+7)

**Common Pitfalls Checklist (Check ALL):**
- [ ] Integer overflow → Use `long long` for sums/products when values > 10⁶
- [ ] Off-by-one errors → Verify loop bounds and array indices
- [ ] Modulo arithmetic → Apply mod correctly if required (especially in multiplication)
- [ ] Disconnected components → For graph problems, handle multiple components
- [ ] Empty input cases → What if N=0 or string is empty?
- [ ] Duplicate values → Problem may assume unique, but test with duplicates
- [ ] Uninitialized variables → Initialize all arrays/variables
- [ ] Array bounds → Ensure array size matches maximum N

### Step 4: Implementation Strategy
Plan the implementation:
- Choose appropriate data types (int vs long long vs double)
- Plan the input reading logic (single vs multiple test cases)
- Structure the algorithm clearly (avoid spaghetti code)
- Add fast I/O if needed (recommended for large inputs)
- Decide on exact output format (trailing spaces, newlines)

### Step 5: Verification Checklist
Before finalizing, verify:
- ✓ Sample inputs produce correct outputs?
- ✓ All edge cases from Step 3 handled?
- ✓ Time complexity within limits?
- ✓ No integer overflow risk?
- ✓ Output format EXACTLY matches problem specification?
- ✓ No debug prints or extra output?

**Optional Mental Dry-Run:**
Trace through 1-2 tricky test cases mentally (can add as comments in code)

═══════════════════════════════════════════════════════════════
## C++ IMPLEMENTATION REQUIREMENTS
═══════════════════════════════════════════════════════════════

### Mandatory Components:
1. **Headers**: Use `#include <bits/stdc++.h>` or specific headers
2. **Fast I/O** (recommended for large inputs):
   ```cpp
   ios_base::sync_with_stdio(false);
   cin.tie(NULL);
   ```
3. **Data Types**: Use `long long` for large numbers (sums/products > 10⁶)
4. **Main Function**: Implement `int main()` with `return 0;`
5. **Clean Code**:
   - No debug prints (cout/cerr/printf for debugging)
   - Clear, self-documenting variable names
   - Minimal comments only (code should be readable)

### Standard Template:
```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read input

    // Implement algorithm

    // Output result

    return 0;
}}
```

═══════════════════════════════════════════════════════════════
## OUTPUT FORMAT (STRICT)
═══════════════════════════════════════════════════════════════

Return your solution in this EXACT format:

```cpp
// YOUR COMPLETE SOLUTION HERE
```

**CRITICAL RULES:**
- Return ONLY ONE code block
- NO explanations before the code block
- NO text after the code block
- NO multiple solutions or alternatives
- NO verbose comments (minimal inline comments only)
- Make sure the code block is properly formatted and complete

If the problem statement is ambiguous, make the least-risk assumption and document it briefly in comments.
"""

        update_progress("Generating solution...")

        # Use optimal temperature based on difficulty
        temperature = self.get_optimal_temperature(difficulty_rating)
        logger.info(f"Generating solution with temperature={temperature} for difficulty={difficulty_rating}")

        # Log the full prompt being sent to Gemini
        logger.info("="*80)
        logger.info("GEMINI SOLUTION GENERATION PROMPT:")
        logger.info("="*80)
        logger.info(prompt)
        logger.info("="*80)

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
            )
        )
        response_text = response.text.strip()

        # Log the Gemini response
        logger.info("="*80)
        logger.info("GEMINI SOLUTION GENERATION RESPONSE:")
        logger.info("="*80)
        logger.info(response_text)
        logger.info("="*80)

        # Extract C++ code
        code_match = re.search(r'```(?:cpp|c\+\+)?\s*([\s\S]*?)```', response_text)
        if code_match:
            solution_code = code_match.group(1).strip()
        else:
            # Try to find code starting with #include
            include_match = re.search(r'(#include[\s\S]*?return\s+0\s*;[\s\S]*?\})', response_text)
            if include_match:
                solution_code = include_match.group(1).strip()
            else:
                raise ValueError('Could not extract C++ code from response')

        if len(solution_code) < 100:
            raise ValueError('Generated code is too short, likely incomplete')

        logger.info(f"Successfully generated solution: {len(solution_code)} characters")

        return {
            'solution_code': solution_code,
            'attempt_number': (previous_attempt.get('attempt_number', 0) + 1) if previous_attempt else 1
        }

    def _parse_problem_url(self, url):
        """Parse platform and problem_id from URL"""
        import re

        if 'codeforces.com' in url:
            match = re.search(r'/problem/(\d+)/([A-Z]\d*)', url)
            if match:
                return 'codeforces', f"{match.group(1)}{match.group(2)}"
        elif 'acmicpc.net' in url or 'baekjoon' in url:
            match = re.search(r'/problem/(\d+)', url)
            if match:
                return 'baekjoon', match.group(1)

        return 'unknown', 'unknown'
