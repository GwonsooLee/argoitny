"""Async code execution service - supports both local and Judge0"""
from django.conf import settings
from .async_judge0_service import AsyncJudge0Service
from .async_code_executor import AsyncCodeExecutor
import logging

logger = logging.getLogger(__name__)


class AsyncCodeExecutionService:
    """Unified async code execution service"""

    @staticmethod
    async def execute_with_test_cases(code, language, test_inputs):
        """
        Execute code with multiple test case inputs (async)

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
        logger.info(f"[AsyncCodeExecutionService] Executing {language} code with {len(test_inputs)} test inputs")
        logger.info(f"[AsyncCodeExecutionService] Code length: {len(code)} chars")
        logger.info(f"[AsyncCodeExecutionService] USE_JUDGE0: {settings.USE_JUDGE0}")

        if settings.USE_JUDGE0:
            # Use Judge0 API (async)
            judge0_service = AsyncJudge0Service()
            return await judge0_service.execute_with_test_cases(code, language, test_inputs)
        else:
            # Use local executor (async)
            logger.info(f"[AsyncCodeExecutionService] Using local AsyncCodeExecutor")
            results = []
            success_count = 0
            error_count = 0

            for idx, test_input in enumerate(test_inputs):
                try:
                    logger.info(f"[AsyncCodeExecutionService] Executing test case {idx+1}/{len(test_inputs)}, input_len={len(test_input)}")
                    result = await AsyncCodeExecutor.execute(code, language, test_input)

                    if result['success']:
                        success_count += 1
                        results.append({
                            'input': test_input,
                            'output': result['output'],
                            'error': None,
                            'status': 'success',
                        })
                        logger.info(f"[AsyncCodeExecutionService] Test case {idx+1} SUCCESS, output_len={len(result['output'])}")
                    else:
                        error_count += 1
                        error_msg = result.get('error', 'Execution failed')
                        results.append({
                            'input': test_input,
                            'output': result.get('output', ''),
                            'error': error_msg,
                            'status': 'error',
                        })
                        logger.error(f"[AsyncCodeExecutionService] Test case {idx+1} FAILED: {error_msg}")
                except Exception as e:
                    error_count += 1
                    results.append({
                        'input': test_input,
                        'output': '',
                        'error': str(e),
                        'status': 'error',
                    })
                    logger.error(f"[AsyncCodeExecutionService] Test case {idx+1} EXCEPTION: {str(e)}", exc_info=True)

            logger.info(f"[AsyncCodeExecutionService] Execution complete: {success_count} success, {error_count} errors")
            return results
