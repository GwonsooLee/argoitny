"""Gemini AI Service"""
import json
import requests
import google.generativeai as genai
from django.conf import settings


class GeminiService:
    """Handle Gemini AI operations"""

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
        else:
            self.model = None

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

            # Get text and clean it up
            text = soup.get_text()

            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)

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
    "solution_code": "C++ code here - MUST be correct and pass all samples"
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
                    if 'MUST be correct' in solution_code or len(solution_code) < 100:
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
                                raise ValueError(f'Generated solution failed sample test cases after {max_attempts} attempts: {validation_error}')

                        logger.info(f'✓ Solution passed all {len(samples)} sample test cases on attempt {attempt}')
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
