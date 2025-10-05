"""Gemini AI Service"""
import json
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

        prompt = f"""You are an expert at creating test case generators for competitive programming problems.

Problem Details:
- Platform: {problem_info['platform']}
- Problem ID: {problem_info['problem_id']}
- Title: {problem_info['title']}
- Language: {problem_info['language']}

Input Constraints:
{problem_info['constraints']}

Task:
Write a Python function that generates diverse test case inputs. The function takes a parameter `n` (number of test cases to generate).

Test Case Distribution:
- 50% should be SMALL inputs (easy to verify, edge cases, minimal values)
- 30% should be MEDIUM inputs (moderate complexity)
- 20% should be LARGE inputs (maximum or near-maximum values to test performance)

IMPORTANT REQUIREMENTS:
- Create a function named `generate_test_cases(n)` that takes the number of cases as parameter
- Returns a list of exactly `n` input strings
- Only use Python standard library (random, math, string, etc.)
- NO external dependencies (no numpy, no external packages)
- Each input should be a string ready to be passed to stdin
- For multi-line inputs, use newline character (\\n)
- Include edge cases: minimum values, maximum values, boundary conditions
- Follow the 50/30/20 distribution for small/medium/large cases

Return ONLY the Python code, NO markdown, NO explanations, NO code blocks:

def generate_test_cases(n):
    import random
    test_cases = []

    # Calculate distribution
    small_count = int(n * 0.5)
    medium_count = int(n * 0.3)
    large_count = n - small_count - medium_count

    # Your code here to generate test cases following the distribution

    return test_cases

Write the complete function now:"""

        try:
            response = self.model.generate_content(prompt)
            code = response.text.strip()

            # Remove markdown code blocks if present
            code = code.replace('```python\n', '').replace('```python', '')
            code = code.replace('```\n', '').replace('```', '')
            code = code.strip()

            # Basic validation
            if 'def generate_test_cases' not in code:
                raise ValueError('Generated code does not contain generate_test_cases function')

            return code

        except Exception as e:
            raise ValueError(f'Failed to generate test case generator code: {str(e)}')
