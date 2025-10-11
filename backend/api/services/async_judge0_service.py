"""Async Judge0 API Service for code execution using httpx"""
import httpx
from django.conf import settings


class AsyncJudge0Service:
    """Async service for executing code using Judge0 API"""

    # Language IDs for Judge0
    LANGUAGE_IDS = {
        'python': 71,  # Python 3.8.1
        'javascript': 63,  # JavaScript (Node.js 12.14.0)
        'cpp': 54,  # C++ (GCC 9.2.0)
        'java': 62,  # Java (OpenJDK 13.0.1)
    }

    def __init__(self):
        self.api_url = settings.JUDGE0_API_URL
        self.api_key = settings.JUDGE0_API_KEY
        self.headers = {
            'Content-Type': 'application/json',
        }
        # Add API key header only if using RapidAPI
        if 'rapidapi' in self.api_url.lower():
            self.headers['X-RapidAPI-Key'] = self.api_key
            self.headers['X-RapidAPI-Host'] = 'judge0-ce.p.rapidapi.com'

    async def execute_code(self, code, language, stdin='', timeout=5):
        """
        Execute code with given input using Judge0 API (async)

        Args:
            code: Source code to execute
            language: Programming language (python, javascript, cpp, java)
            stdin: Input data for the code
            timeout: Maximum execution time in seconds

        Returns:
            dict: {
                'stdout': str,  # Program output
                'stderr': str,  # Error output
                'status': str,  # Status description
                'time': float,  # Execution time
                'memory': int,  # Memory used
            }

        Raises:
            ValueError: If language is not supported
            Exception: If API request fails
        """
        if language not in self.LANGUAGE_IDS:
            raise ValueError(f'Unsupported language: {language}')

        language_id = self.LANGUAGE_IDS[language]

        # Create submission
        submission_data = {
            'source_code': code,
            'language_id': language_id,
            'stdin': stdin,
            'cpu_time_limit': timeout,
        }

        # Submit code using async httpx client
        submit_url = f"{self.api_url}/submissions?base64_encoded=false&wait=true"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                submit_url,
                json=submission_data,
                headers=self.headers
            )

            if not response.is_success:
                raise Exception(f'Judge0 API error: {response.status_code} - {response.text}')

            result = response.json()

        # Parse result
        return {
            'stdout': (result.get('stdout') or '').strip(),
            'stderr': (result.get('stderr') or '').strip(),
            'compile_output': (result.get('compile_output') or '').strip(),
            'status': result.get('status', {}).get('description', 'Unknown'),
            'time': float(result.get('time') or 0),
            'memory': int(result.get('memory') or 0),
        }

    async def execute_with_test_cases(self, code, language, test_inputs):
        """
        Execute code with multiple test case inputs (async)

        Args:
            code: Source code to execute
            language: Programming language
            test_inputs: List of input strings for test cases

        Returns:
            list: List of results for each test case
                [
                    {
                        'input': str,
                        'output': str,
                        'error': str or None,
                        'status': str,
                    },
                    ...
                ]
        """
        results = []

        for test_input in test_inputs:
            try:
                result = await self.execute_code(code, language, stdin=test_input)

                if result['status'] == 'Accepted':
                    results.append({
                        'input': test_input,
                        'output': result['stdout'],
                        'error': None,
                        'status': 'success',
                    })
                else:
                    error_msg = result['stderr'] or result['compile_output'] or result['status']
                    results.append({
                        'input': test_input,
                        'output': result['stdout'],
                        'error': error_msg,
                        'status': 'error',
                    })

            except Exception as e:
                results.append({
                    'input': test_input,
                    'output': '',
                    'error': str(e),
                    'status': 'error',
                })

        return results
