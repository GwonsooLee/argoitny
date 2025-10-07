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

    def generate_test_case_generator_code(self, problem_info):
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

        prompt = f"""You are an expert at creating test case generators for competitive programming problems.

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
   - Where t is the number of cases in that input (can vary, but keep reasonable: 1-5 for small, 5-10 for medium, 10-20 for large)
   - Example: If generating 10 inputs, return 10 strings, each containing multiple test cases

2. If the solution code processes a single test case (no t variable):
   - The generator must return a list of `n` input strings
   - Each string is ONE test case: "<input_data>"

Test Case Distribution:
- 50% should be SMALL inputs (easy to verify, edge cases, minimal values)
- 30% should be MEDIUM inputs (moderate complexity)
- 20% should be LARGE inputs (maximum or near-maximum values to test performance)

IMPORTANT REQUIREMENTS:
- Create a function named `generate_test_cases(n)` that takes the number of cases as parameter
- Returns a list of exactly `n` input strings
- Only use Python standard library (random, math, string, etc.)
- NO external dependencies (no numpy, no external packages)
- Each input string should be ready to be passed directly to stdin
- For multi-line inputs, use newline character (\\n)
- Include edge cases: minimum values, maximum values, boundary conditions
- Follow the 50/30/20 distribution for small/medium/large cases
- Match the EXACT input format from the solution code

CRITICAL: Return ONLY executable Python code. Do NOT include:
- Markdown code blocks (```python or ```)
- Explanations before or after the code
- Comments explaining what the code does
- Any text that is not valid Python syntax

You must return ONLY the function definition starting with "def generate_test_cases(n):" and nothing else.

Example for MULTI-TEST CASE format (if solution has `int t` loop):
def generate_test_cases(n):
    import random
    test_cases = []
    for _ in range(n):
        t = random.randint(1, 5)  # Number of test cases in this input
        cases = []
        for _ in range(t):
            # Generate one test case
            case_data = "..."
            cases.append(case_data)
        test_cases.append(f"{{t}}\\n{{chr(10).join(cases)}}")
    return test_cases

Now write the complete function based on the solution code format:"""

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

    def extract_problem_info_from_url(self, problem_url):
        """
        Extract problem information from URL using Gemini AI

        Args:
            problem_url: URL of the problem page

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
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': random.choice(accept_languages),
                'Accept-Encoding': 'gzip, deflate, br',
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
            for attempt in range(max_retries):
                try:
                    response = session.get(problem_url, timeout=30, allow_redirects=True)

                    if response.status_code == 403:
                        if attempt < max_retries - 1:
                            # Wait longer on retry with exponential backoff
                            wait_time = random.uniform(5, 10) * (attempt + 1)
                            time.sleep(wait_time)

                            # Change User-Agent for retry
                            session.headers['User-Agent'] = random.choice(user_agents)
                            continue
                        else:
                            raise ValueError(f'Failed to fetch problem URL after {max_retries} attempts: 403 Forbidden. The website may be blocking automated requests.')

                    response.raise_for_status()
                    webpage_content = response.text
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        wait_time = random.uniform(3, 6) * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f'Failed to fetch problem URL: {str(e)}')

            # Limit content size to avoid token limits
            if len(webpage_content) > 50000:
                webpage_content = webpage_content[:50000]

            prompt = f"""You are an expert at analyzing competitive programming problems and generating efficient C++ solutions.

Given the following problem webpage content, extract:
1. Problem title
2. Input/output constraints (describe the input format, constraints, and limits)
3. C++ solution code that is optimized for performance

IMPORTANT REQUIREMENTS FOR THE C++ SOLUTION:
- The code must be HIGHLY OPTIMIZED for speed and efficiency
- It must handle the maximum input constraints within time limits
- Use efficient algorithms and data structures (prefer O(n log n) or better when possible)
- Use fast I/O techniques (ios_base::sync_with_stdio(false), cin.tie(NULL))
- Avoid unnecessary operations or slow algorithms
- The solution should be production-quality and pass all test cases efficiently
- NO EXPLANATIONS, NO COMMENTS - only the working C++ code

CRITICAL: You MUST return ONLY a valid JSON object. Do NOT include any text before or after the JSON.

Return your response in EXACTLY this format (replace the content inside quotes):
{{
    "title": "problem title here",
    "constraints": "detailed input/output constraints here",
    "solution_code": "C++ code here (no explanations, no comments, just code)"
}}

Webpage content:
{webpage_content}

Remember: Return ONLY the JSON object above. No additional text, no markdown, no explanations."""

            # Generate response
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            response_text = response_text.replace('```json\n', '').replace('```json', '')
            response_text = response_text.replace('```\n', '').replace('```', '')
            response_text = response_text.strip()

            # Parse JSON response with better error handling
            import re
            import logging
            logger = logging.getLogger(__name__)

            try:
                # First try direct parsing
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f'Direct JSON parse failed: {e}. Attempting to extract JSON from response.')

                # Try to find JSON object in the response
                # Look for the first { and the last }
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    try:
                        result = json.loads(json_str)
                        logger.info('Successfully extracted JSON from response')
                    except json.JSONDecodeError as e2:
                        logger.error(f'Failed to parse extracted JSON: {e2}')
                        logger.error(f'Response text (first 500 chars): {response_text[:500]}')
                        raise ValueError(f'Failed to parse JSON from Gemini response: {str(e2)}')
                else:
                    logger.error(f'No JSON found in response. Response text (first 500 chars): {response_text[:500]}')
                    raise ValueError('No JSON object found in Gemini response')

            # Validate required fields
            if not all(key in result for key in ['title', 'constraints', 'solution_code']):
                missing_fields = [key for key in ['title', 'constraints', 'solution_code'] if key not in result]
                logger.error(f'Missing required fields: {missing_fields}')
                logger.error(f'Received keys: {list(result.keys())}')
                raise ValueError(f'Missing required fields in Gemini response: {missing_fields}')

            return result

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
