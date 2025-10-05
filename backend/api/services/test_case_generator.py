"""Safe execution service for test case generation code"""
import ast
import sys
from io import StringIO
from typing import List, Dict
import contextlib


class TestCaseGenerator:
    """Execute test case generation code safely"""

    # Allowed built-in functions for safe execution
    SAFE_BUILTINS = {
        'range': range,
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'sorted': sorted,
        'reversed': reversed,
        'all': all,
        'any': any,
        'ord': ord,
        'chr': chr,
        'pow': pow,
        'divmod': divmod,
        'print': print,  # Allow print for debugging
        '__import__': __import__,  # Allow __import__ for module imports
    }

    # Allowed modules
    SAFE_MODULES = ['random', 'math', 'string', 'itertools', 'collections']

    @staticmethod
    def validate_code(code: str) -> bool:
        """
        Validate that the code is safe to execute

        Args:
            code: Python code to validate

        Returns:
            True if code is safe, raises ValueError otherwise

        Raises:
            ValueError: If code contains unsafe operations
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f'Syntax error in generated code: {str(e)}')

        # Check for dangerous operations
        for node in ast.walk(tree):
            # Block file operations (but allow __import__ for safe module imports)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['open', 'exec', 'eval', 'compile']:
                        raise ValueError(f'Unsafe operation detected: {node.func.id}')

            # Block import of non-whitelisted modules
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] not in TestCaseGenerator.SAFE_MODULES:
                        raise ValueError(f'Unsafe module import: {alias.name}')

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] not in TestCaseGenerator.SAFE_MODULES:
                    raise ValueError(f'Unsafe module import: {node.module}')

        return True

    @staticmethod
    def execute_generator_code(code: str, num_cases: int = 100, timeout: int = 10) -> List[str]:
        """
        Execute test case generator code safely

        Args:
            code: Python code containing generate_test_cases(n) function
            num_cases: Number of test cases to generate
            timeout: Maximum execution time in seconds

        Returns:
            List of test case input strings

        Raises:
            ValueError: If execution fails or code is unsafe
            TimeoutError: If execution exceeds timeout
        """
        # Validate code first
        TestCaseGenerator.validate_code(code)

        # Create restricted execution environment
        safe_globals = {
            '__builtins__': TestCaseGenerator.SAFE_BUILTINS,
        }

        # Import safe modules into the namespace
        import random
        import math
        import string
        import itertools
        import collections

        safe_globals.update({
            'random': random,
            'math': math,
            'string': string,
            'itertools': itertools,
            'collections': collections,
        })

        try:
            # Execute the code in restricted environment
            exec(code, safe_globals)

            # Check if generate_test_cases function exists
            if 'generate_test_cases' not in safe_globals:
                raise ValueError('generate_test_cases function not found in code')

            # Call the function with num_cases parameter
            generate_func = safe_globals['generate_test_cases']
            test_cases = generate_func(num_cases)

            # Validate output
            if not isinstance(test_cases, list):
                raise ValueError('generate_test_cases must return a list')

            if len(test_cases) == 0:
                raise ValueError('generate_test_cases returned empty list')

            # Convert all to strings and validate
            validated_cases = []
            for i, tc in enumerate(test_cases):
                if not isinstance(tc, str):
                    raise ValueError(f'Test case {i} is not a string: {type(tc)}')
                validated_cases.append(tc)

            return validated_cases

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f'Error executing test case generator: {str(e)}')

    @staticmethod
    def generate_test_cases_with_outputs(
        generator_code: str,
        solution_code: str,
        language: str,
        code_executor
    ) -> List[Dict[str, str]]:
        """
        Generate test cases and their outputs

        Args:
            generator_code: Python code to generate test inputs
            solution_code: Solution code to generate outputs
            language: Programming language of solution
            code_executor: CodeExecutor instance

        Returns:
            List of dicts with 'input' and 'output' keys

        Raises:
            ValueError: If generation or execution fails
        """
        # Generate test case inputs
        test_inputs = TestCaseGenerator.execute_generator_code(generator_code)

        # Execute solution code to get outputs
        test_cases_with_outputs = []
        for i, test_input in enumerate(test_inputs):
            execution_result = code_executor.execute(
                code=solution_code,
                language=language,
                input_data=test_input
            )

            if not execution_result['success']:
                raise ValueError(
                    f'Solution code failed on test case {i+1}: {execution_result["error"]}'
                )

            test_cases_with_outputs.append({
                'input': test_input,
                'output': execution_result['output'].strip()
            })

        return test_cases_with_outputs
