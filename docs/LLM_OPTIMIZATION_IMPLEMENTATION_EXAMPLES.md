# LLM Optimization: Implementation Examples

This document provides concrete code examples for implementing the 3-tier model selection strategy.

---

## 1. Gemini Flash Service (Tier 1)

**File:** `/Users/gwonsoolee/algoitny/backend/api/services/gemini_flash_service.py`

```python
"""Gemini 1.5 Flash Service for Simple Extraction Tasks"""
import json
import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GeminiFlashService:
    """
    Lightweight Gemini Flash (1.5) for simple, high-volume tasks

    Use for:
    - Title extraction
    - Basic constraint parsing
    - URL parsing
    - Simple metadata extraction

    Cost: 94% cheaper than Gemini 2.5 Pro
    Speed: 2-3x faster
    """

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def extract_basic_metadata(self, webpage_content, problem_url):
        """
        Extract basic problem metadata (title, constraints) from webpage

        NOTE: Does NOT extract sample test cases (use Gemini Pro for that)

        Args:
            webpage_content: Cleaned webpage text
            problem_url: Original problem URL

        Returns:
            dict: {
                'title': str,
                'constraints': str,
                'description': str (optional)
            }
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        # Simplified prompt for Flash - clear and concise
        prompt = f"""Extract problem metadata from this competitive programming webpage.

## TASK
Extract ONLY:
1. Problem title (exact text as shown)
2. Input constraints (format, ranges, limits)

## RULES
- Do NOT extract sample test cases
- Do NOT solve the problem
- Be precise with constraint details
- Return valid JSON only

## OUTPUT FORMAT
{{
    "title": "Problem Title",
    "constraints": "First line: integer N (1 ≤ N ≤ 10^5)\\nSecond line: N integers...",
    "description": "Brief description if available"
}}

## WEBPAGE CONTENT
{webpage_content[:50000]}

Return JSON:"""

        try:
            # Generate with Flash (faster, cheaper)
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.0,  # Deterministic
                    'max_output_tokens': 2048,
                }
            )

            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif response_text.startswith('```'):
                response_text = response_text.split('```')[1].split('```')[0].strip()

            result = json.loads(response_text)

            # Validate required fields
            if not result.get('title'):
                raise ValueError('Missing title in extracted data')
            if not result.get('constraints'):
                result['constraints'] = 'No constraints provided'

            logger.info(f"[Flash] Extracted basic metadata: {result['title']}")
            return result

        except Exception as e:
            logger.error(f"[Flash] Error extracting basic metadata: {e}", exc_info=True)
            raise ValueError(f'Failed to extract basic metadata: {str(e)}')

    def extract_tags(self, title, constraints):
        """
        Extract problem tags/categories

        Args:
            title: Problem title
            constraints: Problem constraints

        Returns:
            list: Tags (e.g., ['dynamic-programming', 'graph', 'dfs'])
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        prompt = f"""Classify this competitive programming problem into categories.

## PROBLEM INFO
Title: {title}
Constraints: {constraints[:500]}

## TASK
Return 2-5 tags from this list:
- dynamic-programming
- greedy
- graph
- tree
- dfs
- bfs
- binary-search
- sorting
- math
- number-theory
- string
- implementation
- data-structures
- two-pointers
- sliding-window

## OUTPUT FORMAT
Return JSON array: ["tag1", "tag2", "tag3"]

Tags:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 256,
                }
            )

            response_text = response.text.strip()

            # Parse JSON array
            if response_text.startswith('['):
                tags = json.loads(response_text)
            else:
                # Try to extract array from text
                import re
                match = re.search(r'\[([^\]]+)\]', response_text)
                if match:
                    tags = json.loads('[' + match.group(1) + ']')
                else:
                    tags = []

            logger.info(f"[Flash] Extracted tags: {tags}")
            return tags

        except Exception as e:
            logger.error(f"[Flash] Error extracting tags: {e}")
            return []  # Return empty on failure (non-critical)
```

---

## 2. Claude Sonnet Service (Tier 2)

**File:** `/Users/gwonsoolee/algoitny/backend/api/services/claude_service.py`

```python
"""Claude 3.5 Sonnet Service for Balanced Cost/Performance"""
from anthropic import Anthropic
from django.conf import settings
import re
import logging

logger = logging.getLogger(__name__)


class ClaudeSonnetService:
    """
    Claude 3.5 Sonnet for medium-complexity tasks

    Use for:
    - Medium-difficulty solution generation (1500-2000)
    - Hint generation
    - Code analysis
    - Error diagnosis

    Advantages:
    - 70% cheaper than GPT-5
    - Excellent instruction following
    - 200K context window
    - Prompt caching (90% discount)
    """

    def __init__(self):
        if settings.CLAUDE_API_KEY:
            self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
            self.model = 'claude-3-5-sonnet-20241022'
        else:
            self.client = None
            self.model = None

    def generate_solution_for_problem(self, problem_metadata, difficulty_rating=None,
                                     previous_attempt=None, progress_callback=None):
        """
        Generate C++ solution for competitive programming problem

        Args:
            problem_metadata: dict with title, constraints, samples
            difficulty_rating: Optional difficulty rating (1500-2000 recommended)
            previous_attempt: dict with 'code', 'error' if retry
            progress_callback: Optional callback

        Returns:
            dict: {'solution_code': str, 'attempt_number': int}
        """
        if not self.client:
            raise ValueError('Claude API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        # Build retry context if needed
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

        # Build samples
        samples_str = "\n\n".join([
            f"""Input
{s['input']}
Output
{s['output']}"""
            for s in problem_metadata.get('samples', [])
        ])

        # System prompt with caching
        # Note: Claude caches content marked with cache_control automatically
        system_prompt = """You are a competitive programming expert (Codeforces rating 2500+).

## YOUR TASK
Generate a correct, efficient C++ solution for the given problem.

## SOLUTION REQUIREMENTS
1. **Correctness**: Must pass all sample test cases
2. **Efficiency**: Time complexity must fit within constraints
3. **Code Quality**: Clean, readable C++ code
4. **Fast I/O**: Use ios::sync_with_stdio(false); cin.tie(nullptr);

## PROBLEM-SOLVING APPROACH
1. Understand the problem and constraints
2. Identify algorithm pattern (DP, greedy, graph, etc.)
3. Verify time/space complexity fits constraints
4. Consider edge cases (n=1, n=max, empty input, etc.)
5. Write clean, bug-free implementation

## OUTPUT FORMAT
Return ONLY the C++ code in a code block:
```cpp
#include <iostream>
#include <vector>
// ... (your solution)
```

No explanations, no text before/after code block."""

        # User prompt with problem details
        user_prompt = f"""## PROBLEM: {problem_metadata.get('title')}

## DESCRIPTION
{problem_metadata.get('description', problem_metadata['title'])}

## CONSTRAINTS
{problem_metadata['constraints']}

## SAMPLE TEST CASES
{samples_str}

{retry_context}

Generate C++ solution:"""

        update_progress("Generating solution with Claude 3.5 Sonnet...")

        try:
            # Create message with prompt caching
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0.0,  # Deterministic for code generation
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}  # Cache this system prompt
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract text from response
            response_text = message.content[0].text.strip()

            # Log cache usage (for monitoring)
            usage = message.usage
            logger.info(f"[Claude] Tokens - Input: {usage.input_tokens}, "
                       f"Cached: {getattr(usage, 'cache_read_input_tokens', 0)}, "
                       f"Output: {usage.output_tokens}")

            # Extract C++ code
            solution_code = self._extract_cpp_code(response_text)

            if not solution_code or len(solution_code) < 100:
                raise ValueError(f'Generated code too short ({len(solution_code)} chars)')

            logger.info(f"[Claude] Successfully generated solution: {len(solution_code)} chars")

            return {
                'solution_code': solution_code,
                'attempt_number': (previous_attempt.get('attempt_number', 0) + 1) if previous_attempt else 1
            }

        except Exception as e:
            logger.error(f"[Claude] Error generating solution: {e}", exc_info=True)
            raise ValueError(f'Failed to generate solution: {str(e)}')

    def _extract_cpp_code(self, response_text):
        """Extract C++ code from response"""
        # Method 1: Try code block with language specifier
        code_match = re.search(r'```(?:cpp|c\+\+)?\s*([\s\S]*?)```', response_text)
        if code_match:
            return code_match.group(1).strip()

        # Method 2: Try finding code from #include to return 0;
        include_match = re.search(r'(#include[\s\S]*?return\s+0\s*;[\s\S]*?\})', response_text)
        if include_match:
            return include_match.group(1).strip()

        # Method 3: Use response as-is if it looks like code
        if '#include' in response_text and 'return 0' in response_text:
            return response_text.strip()

        raise ValueError('Could not extract C++ code from response')

    def generate_hints(self, user_code, solution_code, test_failures, problem_info):
        """
        Generate progressive hints for failed code

        Args:
            user_code: Student's code
            solution_code: Correct solution
            test_failures: List of failed test cases
            problem_info: Problem metadata

        Returns:
            list: Progressive hints (3 levels)
        """
        if not self.client:
            raise ValueError('Claude API key not configured')

        # System prompt for hint generation (cached)
        system_prompt = """You are a patient competitive programming tutor.

## YOUR TASK
Generate 3 progressive hints to help a student fix their failing code.

## HINT LEVELS
1. **Hint 1 (Conceptual)**: Identify the high-level issue (algorithm, approach, edge case)
   - DO NOT reveal the solution
   - Focus on understanding the problem

2. **Hint 2 (Specific)**: Point to the specific bug or issue in their code
   - Identify exact location of problem
   - Explain why it's wrong

3. **Hint 3 (Actionable)**: Suggest concrete steps to fix
   - Provide specific guidance
   - DO NOT write code for them

## OUTPUT FORMAT
Return JSON array of hints:
[
    {"level": 1, "hint": "Consider how your algorithm handles...", "type": "conceptual"},
    {"level": 2, "hint": "In line X, your loop condition...", "type": "specific"},
    {"level": 3, "hint": "Try changing your loop to iterate...", "type": "actionable"}
]"""

        # Build failure summary
        failure_summary = "\n".join([
            f"Test {i+1}: {f.get('error', 'Wrong output')}"
            for i, f in enumerate(test_failures[:3])  # Limit to 3 failures
        ])

        user_prompt = f"""## PROBLEM: {problem_info.get('title')}

## STUDENT'S CODE
```cpp
{user_code[:5000]}  // Truncated if too long
```

## FAILED TESTS
{failure_summary}

## CORRECT SOLUTION (for reference only)
```cpp
{solution_code[:3000]}  // Truncated
```

Generate 3 progressive hints:"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.3,  # Slight creativity for hint phrasing
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            response_text = message.content[0].text.strip()

            # Parse JSON hints
            import json

            # Try to find JSON array in response
            if response_text.startswith('['):
                hints = json.loads(response_text)
            else:
                # Try to extract JSON array
                match = re.search(r'\[[\s\S]*\]', response_text)
                if match:
                    hints = json.loads(match.group(0))
                else:
                    # Fallback: Parse as text hints
                    hints = self._parse_text_hints(response_text)

            logger.info(f"[Claude] Generated {len(hints)} hints")
            return hints

        except Exception as e:
            logger.error(f"[Claude] Error generating hints: {e}", exc_info=True)
            # Return generic hints on failure
            return [
                {"level": 1, "hint": "Review your algorithm and check for edge cases.", "type": "conceptual"},
                {"level": 2, "hint": "Check your loop conditions and array bounds.", "type": "specific"},
                {"level": 3, "hint": "Compare your output with expected output line by line.", "type": "actionable"}
            ]

    def _parse_text_hints(self, text):
        """Fallback: Parse hints from plain text"""
        hints = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if line.strip():
                hints.append({
                    "level": min(i + 1, 3),
                    "hint": line.strip(),
                    "type": "general"
                })

            if len(hints) >= 3:
                break

        return hints or [{"level": 1, "hint": "Review your solution logic.", "type": "general"}]
```

---

## 3. Updated LLM Factory with Tier Selection

**File:** `/Users/gwonsoolee/algoitny/backend/api/services/llm_factory.py`

```python
"""LLM Service Factory - Multi-Tier Model Selection"""
from django.conf import settings
from .gemini_service import GeminiService
from .gemini_flash_service import GeminiFlashService
from .openai_service import OpenAIService
from .claude_service import ClaudeSonnetService
import logging

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory to create appropriate LLM service based on task complexity"""

    # Model tier mapping
    TIER_1_MODELS = ['gemini-flash', 'gpt-4o-mini']  # Simple tasks
    TIER_2_MODELS = ['gemini-pro', 'claude-sonnet']  # Balanced
    TIER_3_MODELS = ['gpt-4o', 'gpt-5', 'claude-opus']  # Complex

    @staticmethod
    def create_service(service_type=None):
        """
        Create LLM service instance based on configuration

        Args:
            service_type: Optional override ('gemini', 'openai', 'claude', etc.)
                         If None, uses DEFAULT_LLM_SERVICE from settings

        Returns:
            LLMService instance
        """
        if service_type is None:
            service_type = getattr(settings, 'DEFAULT_LLM_SERVICE', 'gemini').lower()

        logger.info(f"Creating LLM service: {service_type}")

        if service_type == 'gemini':
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                raise ValueError('Gemini API key not configured')
            return GeminiService()

        elif service_type == 'gemini-flash':
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                raise ValueError('Gemini API key not configured')
            return GeminiFlashService()

        elif service_type == 'openai':
            if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
                raise ValueError('OpenAI API key not configured')
            return OpenAIService()

        elif service_type == 'claude':
            if not hasattr(settings, 'CLAUDE_API_KEY') or not settings.CLAUDE_API_KEY:
                raise ValueError('Claude API key not configured')
            return ClaudeSonnetService()

        else:
            raise ValueError(f'Invalid LLM service type: {service_type}')

    @staticmethod
    def create_solution_service(difficulty_rating=None, llm_config=None):
        """
        Select optimal LLM service based on problem difficulty

        Args:
            difficulty_rating: Problem difficulty (800-3500)
            llm_config: Optional override config with 'model' key

        Returns:
            LLMService instance optimized for difficulty level

        Selection Strategy:
        - < 1500: Gemini 2.5 Pro (balanced, good quality)
        - 1500-2000: Claude 3.5 Sonnet (better reasoning, prompt caching)
        - 2000+: GPT-4o or GPT-5 (best for hard problems)
        """
        # Check for explicit model override
        if llm_config and 'model' in llm_config:
            model = llm_config['model'].lower()
            if 'gpt-5' in model or 'o1' in model:
                return LLMServiceFactory.create_service('openai')
            elif 'claude' in model:
                return LLMServiceFactory.create_service('claude')
            elif 'gemini' in model:
                if 'flash' in model:
                    return LLMServiceFactory.create_service('gemini-flash')
                return LLMServiceFactory.create_service('gemini')

        # Difficulty-based selection
        if difficulty_rating is None or difficulty_rating < 1500:
            # Easy problems: Use Gemini Pro (good balance)
            logger.info(f"[Tier Selection] Difficulty {difficulty_rating} → Gemini 2.5 Pro")
            return LLMServiceFactory.create_service('gemini')

        elif difficulty_rating < 2000:
            # Medium problems: Use Claude Sonnet (better reasoning + caching)
            logger.info(f"[Tier Selection] Difficulty {difficulty_rating} → Claude 3.5 Sonnet")
            return LLMServiceFactory.create_service('claude')

        else:
            # Hard problems: Use GPT-4o (best for complex reasoning)
            logger.info(f"[Tier Selection] Difficulty {difficulty_rating} → GPT-4o")
            return LLMServiceFactory.create_service('openai')

    @staticmethod
    def create_extraction_service(task_type='metadata'):
        """
        Select optimal service for extraction tasks

        Args:
            task_type: Type of extraction
                - 'basic': Title, constraints (use Flash)
                - 'samples': Sample test cases (use Pro - accuracy critical)
                - 'metadata': Full metadata (use split approach)

        Returns:
            LLMService instance
        """
        if task_type == 'basic':
            # Use Flash for simple extractions (92% cheaper)
            logger.info("[Tier Selection] Basic extraction → Gemini 1.5 Flash")
            return LLMServiceFactory.create_service('gemini-flash')

        elif task_type == 'samples':
            # Use Pro for sample extraction (accuracy critical)
            logger.info("[Tier Selection] Sample extraction → Gemini 2.5 Pro")
            return LLMServiceFactory.create_service('gemini')

        else:
            # Default to Pro for full metadata
            logger.info("[Tier Selection] Full metadata → Gemini 2.5 Pro")
            return LLMServiceFactory.create_service('gemini')

    @staticmethod
    def create_hint_service(complexity='simple'):
        """
        Select optimal service for hint generation

        Args:
            complexity: Hint complexity
                - 'simple': Basic hints (use Flash or Claude)
                - 'complex': Detailed analysis (use Claude or Gemini Pro)

        Returns:
            LLMService instance
        """
        if complexity == 'simple':
            # Try Claude first for hint generation (good at tutoring)
            try:
                logger.info("[Tier Selection] Simple hints → Claude 3.5 Sonnet")
                return LLMServiceFactory.create_service('claude')
            except ValueError:
                # Fallback to Gemini if Claude not configured
                logger.info("[Tier Selection] Simple hints → Gemini Flash (fallback)")
                return LLMServiceFactory.create_service('gemini-flash')
        else:
            # Use Pro for complex hint analysis
            logger.info("[Tier Selection] Complex hints → Gemini 2.5 Pro")
            return LLMServiceFactory.create_service('gemini')

    @staticmethod
    def get_available_services():
        """Get list of available LLM services based on configured API keys"""
        available = []

        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            available.extend(['gemini', 'gemini-flash'])

        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            available.append('openai')

        if hasattr(settings, 'CLAUDE_API_KEY') and settings.CLAUDE_API_KEY:
            available.append('claude')

        return available


# Convenience functions for backwards compatibility
def get_llm_service(service_type=None):
    """Get LLM service instance"""
    return LLMServiceFactory.create_service(service_type)


def get_solution_service(difficulty_rating=None, llm_config=None):
    """Get optimal service for solution generation"""
    return LLMServiceFactory.create_solution_service(difficulty_rating, llm_config)


def get_extraction_service(task_type='metadata'):
    """Get optimal service for extraction tasks"""
    return LLMServiceFactory.create_extraction_service(task_type)
```

---

## 4. Updated Task with Tiered Selection

**File:** `/Users/gwonsoolee/algoitny/backend/api/tasks.py` (modifications)

```python
# In extract_problem_info_task function, replace metadata extraction section:

# STEP 1: Extract problem metadata using tiered approach
# Use Flash for basic info (92% cheaper), Pro for samples (accuracy critical)

# 1a. Extract basic metadata with Flash
update_progress("📄 Step 1a/3: Extracting basic info with Gemini Flash...")
flash_service = LLMServiceFactory.create_extraction_service('basic')
basic_metadata = flash_service.extract_basic_metadata(webpage_content, problem_url)
logger.info(f"Extracted basic metadata with Flash: {basic_metadata['title']}")

# 1b. Extract samples with Pro (high precision required)
update_progress("📄 Step 1b/3: Extracting samples with Gemini Pro...")
pro_service = LLMServiceFactory.create_extraction_service('samples')
samples = pro_service.extract_problem_metadata_from_url(
    problem_url,
    progress_callback=lambda msg: update_progress(f"📄 {msg}"),
    user_samples=samples  # Pass user-provided samples
).get('samples', [])
logger.info(f"Extracted samples with Pro: {len(samples)} samples")

# 1c. Extract tags with Flash
update_progress("📄 Step 1c/3: Extracting tags...")
tags = flash_service.extract_tags(basic_metadata['title'], basic_metadata['constraints'])
logger.info(f"Extracted tags: {tags}")

# Combine results
problem_metadata = {
    **basic_metadata,
    'samples': samples,
    'tags': tags,
    'platform': platform,
    'problem_id': problem_id
}
```

```python
# In tasks_solution_generation.py, update generate_solution_with_retry:

def generate_solution_with_retry(problem_metadata, update_progress_callback, llm_config=None):
    """
    Generate solution with retry logic and tiered model selection

    Model Selection Strategy:
    - Difficulty < 1500: Gemini 2.5 Pro
    - Difficulty 1500-2000: Claude 3.5 Sonnet
    - Difficulty 2000+: GPT-4o or GPT-5
    """

    # Determine difficulty from metadata
    difficulty = problem_metadata.get('difficulty_rating')

    # Get optimal service for this difficulty
    current_llm_service = LLMServiceFactory.create_solution_service(
        difficulty_rating=difficulty,
        llm_config=llm_config
    )

    service_name = 'unknown'
    if isinstance(current_llm_service, GeminiService):
        service_name = 'gemini'
    elif isinstance(current_llm_service, ClaudeSonnetService):
        service_name = 'claude'
    elif isinstance(current_llm_service, OpenAIService):
        service_name = 'openai'

    logger.info(f"[Solution Generation] Using {service_name} for difficulty {difficulty}")

    # Rest of implementation remains the same...
```

---

## 5. Cost Tracking Utility

**File:** `/Users/gwonsoolee/algoitny/backend/api/utils/llm_cost_tracker.py`

```python
"""LLM Cost Tracking and Monitoring Utility"""
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class LLMCostTracker:
    """Track and log LLM usage costs"""

    # Pricing per 1M tokens (as of Oct 2024)
    PRICES = {
        # OpenAI
        'gpt-4o': {'input': 2.50, 'output': 10.00, 'cached_input': 1.25},
        'gpt-5': {'input': 10.00, 'output': 30.00},  # Estimated
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},

        # Anthropic Claude
        'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00, 'cached_input': 0.30, 'cached_output': 1.50},
        'claude-3-5-haiku': {'input': 0.80, 'output': 4.00, 'cached_input': 0.08, 'cached_output': 0.40},
        'claude-3-opus': {'input': 15.00, 'output': 75.00},

        # Google Gemini
        'gemini-2.5-pro': {'input': 1.25, 'output': 5.00},
        'gemini-1.5-pro': {'input': 1.25, 'output': 5.00},
        'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},
        'gemini-2.0-flash': {'input': 0.00, 'output': 0.00},  # Free during preview
    }

    @staticmethod
    def calculate_cost(model, input_tokens, output_tokens, cached_tokens=0):
        """
        Calculate cost for LLM API call

        Args:
            model: Model name (e.g., 'gpt-4o', 'claude-3-5-sonnet')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached input tokens (Claude/OpenAI)

        Returns:
            float: Cost in USD
        """
        # Normalize model name
        model = model.lower()

        # Find matching price entry
        prices = None
        for model_key, model_prices in LLMCostTracker.PRICES.items():
            if model_key in model:
                prices = model_prices
                break

        if not prices:
            logger.warning(f"Unknown model for cost tracking: {model}")
            return 0.0

        # Calculate cost
        cost = 0.0

        # Input tokens (regular)
        regular_input = input_tokens - cached_tokens
        cost += (regular_input * prices['input']) / 1_000_000

        # Cached input tokens (if applicable)
        if cached_tokens > 0 and 'cached_input' in prices:
            cost += (cached_tokens * prices['cached_input']) / 1_000_000

        # Output tokens
        cost += (output_tokens * prices['output']) / 1_000_000

        return cost

    @staticmethod
    def log_usage(model, input_tokens, output_tokens, task_type,
                  cached_tokens=0, metadata=None):
        """
        Log LLM usage and cost

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            task_type: Type of task (e.g., 'solution_generation', 'metadata_extraction')
            cached_tokens: Cached input tokens
            metadata: Optional dict with additional info
        """
        cost = LLMCostTracker.calculate_cost(
            model, input_tokens, output_tokens, cached_tokens
        )

        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'model': model,
            'task_type': task_type,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cached_tokens': cached_tokens,
            'cost_usd': round(cost, 6),
            'metadata': metadata or {}
        }

        logger.info(f"[LLM Cost] {model} - {task_type} - "
                   f"${cost:.4f} "
                   f"(in={input_tokens}, out={output_tokens}, cached={cached_tokens})")

        # Optionally store in DynamoDB for analytics
        try:
            LLMCostTracker._store_usage_data(log_data)
        except Exception as e:
            logger.error(f"Failed to store usage data: {e}")

    @staticmethod
    def _store_usage_data(log_data):
        """Store usage data in DynamoDB for analytics"""
        from api.dynamodb.client import DynamoDBClient
        from decimal import Decimal
        import time

        table = DynamoDBClient.get_table()

        # Create usage record
        timestamp_ms = int(time.time() * 1000)
        item = {
            'PK': f'LLM_USAGE#{log_data["task_type"]}',
            'SK': str(timestamp_ms),
            'tp': 'llm_usage',
            'dat': {
                'model': log_data['model'],
                'task': log_data['task_type'],
                'in_tok': log_data['input_tokens'],
                'out_tok': log_data['output_tokens'],
                'cache_tok': log_data['cached_tokens'],
                'cost': Decimal(str(log_data['cost_usd'])),
                'meta': log_data['metadata']
            },
            'crt': timestamp_ms
        }

        table.put_item(Item=item)

    @staticmethod
    def get_daily_cost_summary(date=None):
        """
        Get cost summary for a specific date

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            dict: Cost summary by model and task type
        """
        from api.dynamodb.client import DynamoDBClient
        from boto3.dynamodb.conditions import Key
        import time
        from datetime import datetime, timedelta

        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        # Parse date to timestamp range
        dt = datetime.strptime(date, '%Y-%m-%d')
        start_ts = int(dt.timestamp() * 1000)
        end_ts = int((dt + timedelta(days=1)).timestamp() * 1000)

        table = DynamoDBClient.get_table()

        # Query all task types
        summary = {
            'date': date,
            'total_cost': 0.0,
            'by_model': {},
            'by_task': {},
            'total_tokens': {'input': 0, 'output': 0, 'cached': 0}
        }

        task_types = ['solution_generation', 'metadata_extraction', 'hint_generation', 'test_generation']

        for task_type in task_types:
            response = table.query(
                KeyConditionExpression=Key('PK').eq(f'LLM_USAGE#{task_type}') &
                                      Key('SK').between(str(start_ts), str(end_ts))
            )

            for item in response.get('Items', []):
                dat = item.get('dat', {})
                model = dat.get('model', 'unknown')
                cost = float(dat.get('cost', 0))

                # Aggregate by model
                if model not in summary['by_model']:
                    summary['by_model'][model] = 0.0
                summary['by_model'][model] += cost

                # Aggregate by task
                if task_type not in summary['by_task']:
                    summary['by_task'][task_type] = 0.0
                summary['by_task'][task_type] += cost

                # Total cost
                summary['total_cost'] += cost

                # Token counts
                summary['total_tokens']['input'] += dat.get('in_tok', 0)
                summary['total_tokens']['output'] += dat.get('out_tok', 0)
                summary['total_tokens']['cached'] += dat.get('cache_tok', 0)

        return summary
```

---

## 6. Settings Configuration

**File:** `/Users/gwonsoolee/algoitny/backend/config/settings.py` (add these)

```python
# LLM API Keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY', '')  # NEW

# Default LLM Service (for backwards compatibility)
DEFAULT_LLM_SERVICE = os.environ.get('DEFAULT_LLM_SERVICE', 'gemini')

# LLM Model Configuration
LLM_CONFIG = {
    'EXTRACTION': {
        'basic': 'gemini-flash',  # Title, constraints
        'samples': 'gemini-pro',  # Sample test cases (accuracy critical)
        'tags': 'gemini-flash',   # Problem tags
    },
    'SOLUTION': {
        'easy': 'gemini-pro',     # Difficulty < 1500
        'medium': 'claude-sonnet', # Difficulty 1500-2000
        'hard': 'gpt-4o',         # Difficulty 2000+
    },
    'HINTS': {
        'simple': 'claude-sonnet',  # Basic hints
        'complex': 'gemini-pro',    # Detailed analysis
    },
    'TEST_GENERATION': 'gemini-pro',  # Test case generator code
}

# LLM Cost Tracking
LLM_COST_TRACKING_ENABLED = os.environ.get('LLM_COST_TRACKING_ENABLED', 'true').lower() == 'true'
```

**File:** `.env` (add these)

```bash
# Claude API Key (for Tier 2 tasks)
CLAUDE_API_KEY=sk-ant-your-key-here

# LLM Cost Tracking
LLM_COST_TRACKING_ENABLED=true
```

---

## 7. Usage Examples

### Example 1: Extract Problem Metadata (Tiered)

```python
from api.services.llm_factory import LLMServiceFactory

# Extract basic info (cheap)
flash_service = LLMServiceFactory.create_extraction_service('basic')
basic_info = flash_service.extract_basic_metadata(webpage_content, url)

# Extract samples (accurate)
pro_service = LLMServiceFactory.create_extraction_service('samples')
samples = pro_service.extract_problem_metadata_from_url(url).get('samples', [])

# Combine
metadata = {**basic_info, 'samples': samples}
```

### Example 2: Generate Solution (Difficulty-Based)

```python
from api.services.llm_factory import LLMServiceFactory

# Automatic tier selection based on difficulty
service = LLMServiceFactory.create_solution_service(difficulty_rating=1800)
solution = service.generate_solution_for_problem(problem_metadata)

# Logs: "[Tier Selection] Difficulty 1800 → Claude 3.5 Sonnet"
```

### Example 3: Track Costs

```python
from api.utils.llm_cost_tracker import LLMCostTracker

# Log usage
LLMCostTracker.log_usage(
    model='claude-3-5-sonnet',
    input_tokens=4500,
    output_tokens=3200,
    cached_tokens=2000,
    task_type='solution_generation',
    metadata={'difficulty': 1800, 'platform': 'codeforces'}
)

# Get daily summary
summary = LLMCostTracker.get_daily_cost_summary('2025-10-11')
print(f"Total cost: ${summary['total_cost']:.2f}")
print(f"By model: {summary['by_model']}")
```

---

## Testing Checklist

- [ ] Test Gemini Flash extraction on 10 problems
- [ ] Test Claude Sonnet solution generation on medium problems (1500-2000)
- [ ] Test GPT-4o solution generation on hard problems (2000+)
- [ ] Verify prompt caching works (check logs for cached_tokens > 0)
- [ ] Compare solution quality across models
- [ ] Measure actual costs for 100 problems
- [ ] Test fallback logic (disable one API key)
- [ ] Verify cost tracking stores data correctly

---

**Next Steps:**
1. Add Claude API key to environment
2. Copy these service files to your codebase
3. Update imports in existing code
4. Run tests on sample problems
5. Monitor costs and quality for 1 week
6. Adjust tier thresholds if needed
