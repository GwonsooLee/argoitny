"""OpenAI Service for competitive programming problem solving"""
import json
import requests
from django.conf import settings
from openai import OpenAI


class OpenAIService:
    """Handle OpenAI API operations for competitive programming"""

    def __init__(self):
        if settings.OPENAI_API_KEY:
            # Set timeout to 30 minutes (1800 seconds) for long-running requests
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=1800.0)
            # Use GPT-5 for best results, or allow configuration
            self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-5')
        else:
            self.client = None
            self.model = None

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
            extracted_tags = []

            # Codeforces: Extract problem statement div and tags
            if 'codeforces.com' in problem_url:
                problem_div = soup.find('div', class_='problem-statement')
                if problem_div:
                    problem_content = problem_div
                    logger.info("Found Codeforces problem-statement div")
                else:
                    logger.warning("Could not find problem-statement div, using full content")

                # Extract tags from tag-box class
                tag_elements = soup.find_all('span', class_='tag-box')
                if tag_elements:
                    for tag_elem in tag_elements:
                        tag_text = tag_elem.get_text(strip=True).lower()
                        # Remove special characters and asterisks
                        tag_text = tag_text.replace('*', '').strip()
                        if tag_text and tag_text not in extracted_tags:
                            extracted_tags.append(tag_text)
                    logger.info(f"Extracted {len(extracted_tags)} tags from Codeforces: {extracted_tags}")
                else:
                    logger.warning("Could not find tag-box elements on Codeforces page")

            # Baekjoon: Extract problem content and tags
            elif 'acmicpc.net' in problem_url:
                problem_div = soup.find('div', id='problem-body') or soup.find('div', id='problem_description')
                if problem_div:
                    problem_content = problem_div
                    logger.info("Found Baekjoon problem content div")
                else:
                    logger.warning("Could not find problem body div, using full content")

                # Extract tags from problem-tag or algorithm tags
                tag_section = soup.find('div', class_='problem-tag') or soup.find('section', id='problem_tags')
                if tag_section:
                    tag_links = tag_section.find_all('a')
                    for tag_link in tag_links:
                        tag_text = tag_link.get_text(strip=True).lower()
                        # Clean up Korean classification markers
                        tag_text = tag_text.replace('분류:', '').replace('알고리즘:', '').strip()
                        if tag_text and tag_text not in extracted_tags:
                            extracted_tags.append(tag_text)
                    logger.info(f"Extracted {len(extracted_tags)} tags from Baekjoon: {extracted_tags}")
                else:
                    logger.warning("Could not find tag section on Baekjoon page")

            if problem_content:
                soup = BeautifulSoup(str(problem_content), 'html.parser')

            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            text = soup.get_text(separator=' ', strip=True)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)
            webpage_content = re.sub(r' +', ' ', webpage_content)

            # Remove LaTeX math delimiters ($$) from Codeforces content
            webpage_content = re.sub(r'\$\$\$([^\$]+)\$\$\$', r'\1', webpage_content)

            if len(webpage_content) > 80000:
                webpage_content = webpage_content[:80000]

            logger.info(f"Fetched webpage: {len(webpage_content)} chars")

            # System context: Role, rules, and output format
            system_context = """You are a competitive programming problem parser specializing in extracting problem metadata.

## YOUR ROLE
Extract problem metadata in structured JSON format. DO NOT solve the problem or generate code.

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
{
    "title": "Problem Title",
    "constraints": "First line: integer N (1 ≤ N ≤ 10^5)...",
    "samples": [
        {"input": "3\\n1 2 3", "output": "6"},
        {"input": "1\\n100", "output": "100"}
    ]
}"""

            # User context: Actual data to process
            user_prompt = f"""Extract the problem metadata from the following webpage content.

## WEBPAGE CONTENT
{webpage_content}

Return ONLY valid JSON."""

            update_progress("Extracting problem metadata...")

            completion = self.client.responses.create(
                model=self.model,
                instructions=system_context,
                input=user_prompt,
                modalities={"type": "json_object"},
                text={"format": {"type": "text"}, "verbosity": "low"},
                max_output_tokens=4096,
            )

            # Extract text from OpenAI API response (responses.create format)
            response_text = None

            # Try structure 1: completion.output[0].content[0].text (GPT-5 responses format)
            try:
                if hasattr(completion, 'output') and completion.output and len(completion.output) > 0:
                    if hasattr(completion.output[0], 'content') and completion.output[0].content and len(completion.output[0].content) > 0:
                        response_text = completion.output[0].content[0].text.strip()
                        logger.info(f"✓ Extracted using output[0].content[0].text format")
            except Exception as e:
                logger.warning(f"Failed to extract using output[0].content[0].text: {e}")

            # Try structure 2: completion.choices[0].message.content (chat format fallback)
            if not response_text:
                try:
                    if hasattr(completion, 'choices') and completion.choices and len(completion.choices) > 0:
                        if hasattr(completion.choices[0], 'message') and completion.choices[0].message:
                            response_text = completion.choices[0].message.content.strip()
                            logger.info(f"✓ Extracted using choices[0].message.content format")
                except Exception as e:
                    logger.warning(f"Failed to extract using choices[0].message.content: {e}")

            if not response_text:
                logger.error(f"OpenAI response object: {completion}")
                raise ValueError('Could not extract text from OpenAI response')

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

            # Add extracted tags
            if extracted_tags:
                result['tags'] = extracted_tags
                logger.info(f"Extracted: {result['title']}, {len(result.get('samples', []))} samples, {len(extracted_tags)} tags: {extracted_tags}")
            else:
                result['tags'] = []
                logger.info(f"Extracted: {result['title']}, {len(result.get('samples', []))} samples, no tags found")

            return result

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            raise ValueError(f'Failed to extract: {str(e)}')

    def generate_solution_for_problem(self, problem_metadata, difficulty_rating=None, previous_attempt=None, progress_callback=None, llm_config=None):
        """
        Step 2: Generate solution code for the extracted problem

        Args:
            problem_metadata: dict with title, constraints, samples
            difficulty_rating: Optional difficulty rating
            previous_attempt: dict with 'code', 'error' if retry
            progress_callback: Optional callback
            llm_config: Optional LLM configuration dict with model, reasoning_effort, max_output_tokens

        Returns:
            dict: {'solution_code': str, 'attempt_number': int}
        """
        # Apply default LLM config if not provided
        if llm_config is None:
            llm_config = {
                'model': 'gpt-5',
                'reasoning_effort': 'medium',
                'max_output_tokens': 8192
            }
        import logging
        import re

        logger = logging.getLogger(__name__)

        if not self.client:
            raise ValueError('OpenAI API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        # Build minimal retry context (GPT-5 reasoning will handle root cause analysis)
        retry_context = ""
        if previous_attempt:
            retry_context = f"""
Previous attempt failed:
```cpp
{previous_attempt.get('code', 'N/A')}
```

Error: {previous_attempt.get('error', 'Unknown error')}

Fix the issue and provide a corrected solution.
"""

        # Build samples (raw format - like Gemini)
        samples_str = "\n\n".join([
            f"""Input
{s['input']}
Output
{s['output']}"""
            for i, s in enumerate(problem_metadata.get('samples', []))
        ])

        # Balanced system context: Clear rules without over-constraining
        system_context = """You are a competitive programming solver for Codeforces (rating 3000+).
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

        # User context: Raw problem presentation (without samples)
        user_prompt = f"""{problem_metadata.get('description', problem_metadata['title'])}

{problem_metadata['constraints']}
{retry_context}

Solve this problem in C++17."""

        update_progress("Generating solution...")

        # Log the full prompt being sent to OpenAI (DEBUG level for normal operation, INFO for important details)
        logger.info("="*80)
        logger.info("OPENAI SOLUTION GENERATION PROMPT:")
        logger.info("="*80)
        logger.debug(f"INSTRUCTIONS:\n{system_context}")
        logger.info("="*80)
        logger.debug(f"INPUT:\n{user_prompt}")
        logger.info("="*80)

        # GPT-5 parameters from llm_config
        reasoning_effort = llm_config.get('reasoning_effort', 'medium')
        max_output_tokens = llm_config.get('max_output_tokens', 8192)

        logger.info(f"[LLM Config] reasoning_effort={reasoning_effort}, max_output_tokens={max_output_tokens}")

        completion = self.client.responses.create(
            model=self.model,
            instructions=system_context,
            input=user_prompt,
            reasoning={"effort": reasoning_effort},
            text={"format": {"type": "text"}, "verbosity": "low"},
            max_output_tokens=max_output_tokens,
        )

        # Extract text from OpenAI API response (responses.create format for GPT-5)
        logger.debug(f"Completion type: {type(completion)}")
        logger.debug(f"Completion attributes: {dir(completion)}")

        response_text = None

        # Try structure 1: completion.output - find ResponseOutputMessage (skip ResponseReasoningItem)
        try:
            if hasattr(completion, 'output') and completion.output and len(completion.output) > 0:
                # Find the first output item with type='message' (skip reasoning items)
                for output_item in completion.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and output_item.content and len(output_item.content) > 0:
                            response_text = output_item.content[0].text.strip()
                            logger.info(f"✓ Extracted using output[i].content[0].text format (i={completion.output.index(output_item)})")
                            break
        except Exception as e:
            logger.debug(f"Failed to extract using output[i].content[0].text: {e}")

        # Try structure 2: completion.choices[0].message.content (chat format fallback)
        if not response_text:
            try:
                if hasattr(completion, 'choices') and completion.choices and len(completion.choices) > 0:
                    if hasattr(completion.choices[0], 'message') and completion.choices[0].message:
                        response_text = completion.choices[0].message.content.strip()
                        logger.info(f"✓ Extracted using choices[0].message.content format")
            except Exception as e:
                logger.debug(f"Failed to extract using choices[0].message.content: {e}")

        if not response_text:
            logger.error(f"OpenAI response object: {completion}")
            raise ValueError('Could not extract text from OpenAI response - check logs above')

        # Log the OpenAI response (INFO level for normal operation, DEBUG for full content)
        logger.info("="*80)
        logger.info("OPENAI SOLUTION GENERATION RESPONSE:")
        logger.info(f"Response length: {len(response_text)} characters")
        logger.info("="*80)
        logger.debug(f"Full response:\n{response_text}")
        logger.info("="*80)

        # Extract C++ code with multiple fallback methods
        solution_code = None

        # Method 1: Try code block with language specifier (```cpp ... ```)
        code_match = re.search(r'```(?:cpp|c\+\+)?\s*([\s\S]*?)```', response_text)
        if code_match:
            solution_code = code_match.group(1).strip()
            logger.info(f"✓ Extracted C++ from code block ({len(solution_code)} chars)")

        # Method 2: Try finding code from #include to return 0;
        if not solution_code or len(solution_code) < 100:
            include_match = re.search(r'(#include[\s\S]*?return\s+0\s*;[\s\S]*?\})', response_text)
            if include_match:
                solution_code = include_match.group(1).strip()
                logger.info(f"✓ Extracted C++ from #include pattern ({len(solution_code)} chars)")

        # Method 3: Try finding any code block without language specifier (``` ... ```)
        if not solution_code or len(solution_code) < 100:
            generic_block = re.search(r'```\s*\n(#include[\s\S]*?)\n```', response_text)
            if generic_block:
                solution_code = generic_block.group(1).strip()
                logger.info(f"✓ Extracted C++ from generic code block ({len(solution_code)} chars)")

        # Method 4: Try finding code starting from #include to end of response
        if not solution_code or len(solution_code) < 100:
            # Find #include and extract until end, stopping at non-code markers
            if '#include' in response_text:
                start_idx = response_text.find('#include')
                # Stop at common text markers
                end_markers = ['\n\nNote:', '\n\nThis code', '\n\nExplanation:', '\n\n---', '\n\nThe solution']
                end_idx = len(response_text)
                for marker in end_markers:
                    marker_idx = response_text.find(marker, start_idx)
                    if marker_idx != -1:
                        end_idx = min(end_idx, marker_idx)

                potential_code = response_text[start_idx:end_idx].strip()
                if potential_code and len(potential_code) >= 100:
                    solution_code = potential_code
                    logger.info(f"✓ Extracted C++ from #include to end ({len(solution_code)} chars)")

        if not solution_code:
            logger.error(f"Could not extract C++ code. Response preview: {response_text[:500]}")
            raise ValueError('Could not extract C++ code from OpenAI response')

        if len(solution_code) < 100:
            logger.error(f"Generated code too short ({len(solution_code)} chars): {solution_code}")
            raise ValueError(f'Generated code too short ({len(solution_code)} chars)')

        logger.info(f"Successfully generated solution: {len(solution_code)} chars")

        return {
            'solution_code': solution_code,
            'attempt_number': (previous_attempt.get('attempt_number', 0) + 1) if previous_attempt else 1
        }

    def generate_test_case_generator_code(self, problem_info, previous_failure=None, size='mixed'):
        """Generate Python code for test case generation (similar to Gemini)

        Args:
            problem_info: Dict containing problem details
            previous_failure: Dict containing previous failure info (optional)
            size: str - 'small', 'medium', 'large', or 'mixed' (default)
        """
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
