"""Code execution service - supports both local and Judge0"""
from django.conf import settings
from .judge0_service import Judge0Service
from .code_executor import CodeExecutor


class CodeExecutionService:
    """Unified code execution service"""

    @staticmethod
    def execute_with_test_cases(code, language, test_inputs):
        """
        Execute code with multiple test case inputs

        Uses Judge0 if USE_JUDGE0=true, otherwise uses local executor

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
        if settings.USE_JUDGE0:
            # Use Judge0 API
            judge0_service = Judge0Service()
            return judge0_service.execute_with_test_cases(code, language, test_inputs)
        else:
            # Use local executor
            results = []
            for test_input in test_inputs:
                try:
                    result = CodeExecutor.execute(code, language, test_input)

                    if result['success']:
                        results.append({
                            'input': test_input,
                            'output': result['output'],
                            'error': None,
                            'status': 'success',
                        })
                    else:
                        results.append({
                            'input': test_input,
                            'output': result.get('output', ''),
                            'error': result.get('error', 'Execution failed'),
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
