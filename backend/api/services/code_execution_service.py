"""Code execution service - supports both local and Judge0"""
from django.conf import settings
from .judge0_service import Judge0Service
from .code_executor import CodeExecutor
import logging

logger = logging.getLogger(__name__)


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
        logger.info(f"[CodeExecutionService] Executing {language} code with {len(test_inputs)} test inputs")
        logger.info(f"[CodeExecutionService] Code length: {len(code)} chars")
        logger.info(f"[CodeExecutionService] USE_JUDGE0: {settings.USE_JUDGE0}")

        if settings.USE_JUDGE0:
            # Use Judge0 API
            judge0_service = Judge0Service()
            return judge0_service.execute_with_test_cases(code, language, test_inputs)
        else:
            # Use local executor
            logger.info(f"[CodeExecutionService] Using local CodeExecutor")
            results = []
            success_count = 0
            error_count = 0

            for idx, test_input in enumerate(test_inputs):
                try:
                    logger.info(f"[CodeExecutionService] Executing test case {idx+1}/{len(test_inputs)}, input_len={len(test_input)}")
                    result = CodeExecutor.execute(code, language, test_input)

                    if result['success']:
                        success_count += 1
                        results.append({
                            'input': test_input,
                            'output': result['output'],
                            'error': None,
                            'status': 'success',
                        })
                        logger.info(f"[CodeExecutionService] Test case {idx+1} SUCCESS, output_len={len(result['output'])}")
                    else:
                        error_count += 1
                        error_msg = result.get('error', 'Execution failed')
                        results.append({
                            'input': test_input,
                            'output': result.get('output', ''),
                            'error': error_msg,
                            'status': 'error',
                        })
                        logger.error(f"[CodeExecutionService] Test case {idx+1} FAILED: {error_msg}")
                except Exception as e:
                    error_count += 1
                    results.append({
                        'input': test_input,
                        'output': '',
                        'error': str(e),
                        'status': 'error',
                    })
                    logger.error(f"[CodeExecutionService] Test case {idx+1} EXCEPTION: {str(e)}", exc_info=True)

            logger.info(f"[CodeExecutionService] Execution complete: {success_count} success, {error_count} errors")
            return results
