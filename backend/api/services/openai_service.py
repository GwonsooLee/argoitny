"""OpenAI Service for competitive programming problem solving"""
import json
import requests
from django.conf import settings
from openai import OpenAI


class OpenAIService:
    """Handle OpenAI API operations for competitive programming"""

    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            # Use GPT-4o for best results, or allow configuration
            self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o')
        else:
            self.client = None
            self.model = None

    def get_optimal_temperature(self, difficulty_rating):
        """
        Get optimal temperature based on problem difficulty
        Lower temperature = more deterministic (better for hard problems)
        Higher temperature = more creative (better for easy problems)
        """
        if difficulty_rating is None:
            return 0.7
        elif difficulty_rating >= 2500:
            return 0.3  # Very deterministic for 2500+ problems
        elif difficulty_rating >= 2000:
            return 0.5
        elif difficulty_rating >= 1500:
            return 0.7
        else:
            return 0.8

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

    def extract_problem_metadata_from_url(self, problem_url, difficulty_rating=None, progress_callback=None):
        """
        Step 1: Extract only problem metadata (title, constraints, samples) from URL

        Args:
            problem_url: URL to the problem page
            difficulty_rating: Optional difficulty rating
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
        from bs4 import BeautifulSoup
        import time
        import random

        logger = logging.getLogger(__name__)

        if not self.client:
            raise ValueError('OpenAI API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        try:
            # Fetch webpage content (same as Gemini)
            update_progress("Fetching webpage...")

            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            time.sleep(random.uniform(3, 7))

            session = requests.Session()
            session.headers.update(headers)

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = session.get(problem_url, timeout=30, allow_redirects=True)
                    if response.status_code == 403:
                        if attempt < max_retries - 1:
                            time.sleep(random.uniform(5, 10) * (attempt + 1))
                            continue
                        else:
                            raise ValueError('Failed to fetch: 403 Forbidden')
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(3, 6) * (attempt + 1))
                        continue
                    else:
                        raise ValueError(f'Failed to fetch: {str(e)}')

            # Extract clean text from HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            update_progress("Extracting problem content...")
            problem_content = None

            if 'codeforces.com' in problem_url:
                problem_div = soup.find('div', class_='problem-statement')
                if problem_div:
                    problem_content = problem_div
            elif 'acmicpc.net' in problem_url:
                problem_div = soup.find('div', id='problem-body') or soup.find('div', id='problem_description')
                if problem_div:
                    problem_content = problem_div

            if problem_content:
                soup = BeautifulSoup(str(problem_content), 'html.parser')

            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            text = soup.get_text(separator=' ', strip=True)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)
            webpage_content = re.sub(r' +', ' ', webpage_content)

            if len(webpage_content) > 80000:
                webpage_content = webpage_content[:80000]

            logger.info(f"Fetched webpage: {len(webpage_content)} chars")

            # Build prompt for OpenAI
            prompt = f"""You are a competitive programming problem parser specializing in extracting problem metadata.

## YOUR TASK
Extract the problem metadata in structured JSON format. DO NOT solve the problem or generate code.

## EXTRACTION REQUIREMENTS

### 1. Title
- Extract the EXACT problem title as displayed on the page

### 2. Constraints (INPUT FORMAT ONLY)
Extract with PRECISE detail:
- First line format: "First line contains..."
- Subsequent line formats: "Next N lines contain..."
- Variable ranges: "1 ≤ N ≤ 10^5" or "1 ≤ N ≤ 100000"
- Multi-test case format if applicable
- Array/sequence formats
- String constraints

DO NOT include output format, time limits, or problem descriptions.

### 3. Sample Test Cases - CRITICAL EXTRACTION RULES

⚠️ EXTREME PRECISION REQUIRED: These samples will be used for automated C++ solution validation.

**Identification Patterns:**
- Input indicators: "Input", "Sample Input", "예제 입력", "stdin", "Example Input"
- Output indicators: "Output", "Sample Output", "예제 출력", "stdout", "Example Output"

**Extraction Rules:**
1. Extract ONLY data lines (no labels like "Input:", "Output:")
2. Each character, space, newline must be EXACTLY as shown
3. DO NOT add quotes, brackets, or wrapper characters
4. DO NOT modify whitespace or newlines
5. Preserve leading zeros (e.g., "007" not "7")

**Common Mistakes to AVOID:**
❌ Including labels: "Input: 3\\n1 2 3" → ✓ Should be: "3\\n1 2 3"
❌ Changing newlines: "3 1 2 3" → ✓ Should be: "3\\n1 2 3" (if on separate lines)
❌ Removing trailing spaces or newlines

**Multiple Samples:**
- Extract ALL samples (typically 2-5)
- Keep as separate entries
- Use \\n for newlines in JSON

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no code blocks):
{{
    "title": "Problem Title",
    "constraints": "First line: integer N (1 ≤ N ≤ 10^5)...",
    "samples": [
        {{"input": "3\\n1 2 3", "output": "6"}},
        {{"input": "1\\n100", "output": "100"}}
    ]
}}

## WEBPAGE CONTENT
{webpage_content}

Return ONLY valid JSON."""

            update_progress("Extracting problem metadata...")

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from competitive programming problems. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for extraction
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            response_text = completion.choices[0].message.content.strip()
            logger.info(f"OpenAI response: {len(response_text)} chars")

            # Parse JSON
            result = json.loads(response_text)

            # Validate required fields
            if not result.get('title') or result.get('title').strip() == '':
                raise ValueError('Missing title in extracted data')
            if not result.get('constraints'):
                result['constraints'] = 'No constraints provided'

            # Parse problem URL
            platform, problem_id = self._parse_problem_url(problem_url)
            result['platform'] = platform
            result['problem_id'] = problem_id

            logger.info(f"Extracted: {result['title']}, {len(result.get('samples', []))} samples")
            return result

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            raise ValueError(f'Failed to extract: {str(e)}')

    def generate_solution_for_problem(self, problem_metadata, difficulty_rating=None, previous_attempt=None, progress_callback=None):
        """
        Step 2: Generate solution code for the extracted problem

        Args:
            problem_metadata: dict with title, constraints, samples
            difficulty_rating: Optional difficulty rating
            previous_attempt: dict with 'code', 'error' if retry
            progress_callback: Optional callback

        Returns:
            dict: {'solution_code': str, 'attempt_number': int}
        """
        import logging
        import re

        logger = logging.getLogger(__name__)

        if not self.client:
            raise ValueError('OpenAI API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        # Build retry context
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
4. **Implementation Bugs**: Off-by-one errors? Integer overflow? Array bounds?

### Your Task Now:
Generate a CORRECTED solution that fixes the specific failure above.
"""

        # Build samples
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

        prompt = f"""You are an ELITE competitive programmer (Grandmaster level) specializing in Codeforces, ICPC, and IOI problems.

Follow this EXACT protocol to solve the problem:

## PROBLEM
**Title:** {problem_metadata['title']}

**Input Format and Constraints:**
{problem_metadata['constraints']}{constraints_hint}

**Sample Test Cases:**
{samples_str}

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
Select the appropriate algorithm:
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

If the problem statement is ambiguous, make the least-risk assumption and document it briefly in comments."""

        update_progress("Generating solution...")

        temperature = self.get_optimal_temperature(difficulty_rating)
        logger.info(f"Using temperature={temperature}")

        # Log the full prompt being sent to OpenAI
        logger.info("="*80)
        logger.info("OPENAI SOLUTION GENERATION PROMPT:")
        logger.info("="*80)
        logger.info(prompt)
        logger.info("="*80)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert competitive programmer. Generate correct, optimized C++ solutions."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )

        response_text = completion.choices[0].message.content.strip()

        # Log the OpenAI response
        logger.info("="*80)
        logger.info("OPENAI SOLUTION GENERATION RESPONSE:")
        logger.info("="*80)
        logger.info(response_text)
        logger.info("="*80)

        # Extract C++ code
        code_match = re.search(r'```(?:cpp|c\+\+)?\s*([\s\S]*?)```', response_text)
        if code_match:
            solution_code = code_match.group(1).strip()
        else:
            include_match = re.search(r'(#include[\s\S]*?return\s+0\s*;[\s\S]*?\})', response_text)
            if include_match:
                solution_code = include_match.group(1).strip()
            else:
                raise ValueError('Could not extract C++ code')

        if len(solution_code) < 100:
            raise ValueError('Generated code too short')

        logger.info(f"Generated solution: {len(solution_code)} chars")

        return {
            'solution_code': solution_code,
            'attempt_number': (previous_attempt.get('attempt_number', 0) + 1) if previous_attempt else 1
        }

    def generate_test_case_generator_code(self, problem_info, previous_failure=None):
        """Generate Python code for test case generation (similar to Gemini)"""
        if not self.client:
            raise ValueError('OpenAI API key not configured')

        # Similar implementation to Gemini service
        # This is a simplified version - you can expand it
        raise NotImplementedError("Test case generation with OpenAI not yet implemented. Use Gemini for this feature.")

    def generate_hints(self, user_code, solution_code, test_failures, problem_info):
        """Generate progressive hints (similar to Gemini)"""
        if not self.client:
            raise ValueError('OpenAI API key not configured')

        # Similar implementation to Gemini service
        # This is a simplified version - you can expand it
        raise NotImplementedError("Hint generation with OpenAI not yet implemented. Use Gemini for this feature.")

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
