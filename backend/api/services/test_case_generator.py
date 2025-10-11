"""Safe execution service for test case generation code"""
import ast
import sys
import os
import tempfile
import json
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
    def _check_undefined_names(tree: ast.AST, code: str) -> None:
        """
        Check for undefined names in the code using static analysis

        Args:
            tree: AST tree of the code
            code: Original code string for error messages

        Raises:
            ValueError: If undefined names are found
        """
        # Built-in names that are always available
        builtin_names = set(TestCaseGenerator.SAFE_BUILTINS.keys())
        builtin_names.update(['True', 'False', 'None'])

        # Track defined names at module level and function level
        class NameChecker(ast.NodeVisitor):
            def __init__(self):
                self.defined_names = set(builtin_names)
                self.undefined_names = []
                self.current_scope_stack = [set()]  # Stack of scopes

            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    self.current_scope_stack[-1].add(name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    self.current_scope_stack[-1].add(name)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                # Add function name to current scope
                self.current_scope_stack[-1].add(node.name)

                # Create new scope for function body
                self.current_scope_stack.append(set())

                # Add parameters to function scope
                for arg in node.args.args:
                    self.current_scope_stack[-1].add(arg.arg)

                # Visit function body
                for child in node.body:
                    self.visit(child)

                # Pop function scope
                self.current_scope_stack.pop()

            def visit_Assign(self, node):
                # Add assigned names to current scope
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.current_scope_stack[-1].add(target.id)
                    elif isinstance(target, (ast.Tuple, ast.List)):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                self.current_scope_stack[-1].add(elt.id)
                self.generic_visit(node)

            def visit_For(self, node):
                # Add loop variable to current scope
                if isinstance(node.target, ast.Name):
                    self.current_scope_stack[-1].add(node.target.id)
                elif isinstance(node.target, (ast.Tuple, ast.List)):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            self.current_scope_stack[-1].add(elt.id)
                self.generic_visit(node)

            def visit_With(self, node):
                # Add context manager variables to current scope
                for item in node.items:
                    if item.optional_vars:
                        if isinstance(item.optional_vars, ast.Name):
                            self.current_scope_stack[-1].add(item.optional_vars.id)
                self.generic_visit(node)

            def visit_comprehension(self, node):
                # Add comprehension variables
                if isinstance(node.target, ast.Name):
                    self.current_scope_stack[-1].add(node.target.id)
                self.generic_visit(node)

            def visit_Name(self, node):
                # Check if name is being loaded (used) and not defined
                if isinstance(node.ctx, ast.Load):
                    # Check all scopes from innermost to outermost
                    is_defined = False
                    for scope in reversed(self.current_scope_stack):
                        if node.id in scope:
                            is_defined = True
                            break

                    if not is_defined and node.id not in self.defined_names:
                        self.undefined_names.append((node.id, node.lineno, node.col_offset))

                self.generic_visit(node)

        checker = NameChecker()
        checker.visit(tree)

        if checker.undefined_names:
            # Get first undefined name for error message
            name, line, col = checker.undefined_names[0]
            code_lines = code.split('\n')
            error_line = code_lines[line - 1] if line <= len(code_lines) else ''

            raise ValueError(
                f'Undefined name detected: "{name}" at line {line}\n'
                f'Line: {error_line.strip()}\n'
                f'This variable/constant must be defined before use.'
            )

    @staticmethod
    def validate_code(code: str) -> bool:
        """
        Validate that the code is safe to execute and has no undefined names

        Args:
            code: Python code to validate

        Returns:
            True if code is safe, raises ValueError otherwise

        Raises:
            ValueError: If code contains unsafe operations or undefined names
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

        # Check for undefined names
        TestCaseGenerator._check_undefined_names(tree, code)

        return True

    @staticmethod
    def execute_generator_code(code: str, num_cases: int = 100, timeout: int = 10, size: str = 'mixed') -> List[str]:
        """
        Execute test case generator code safely

        Args:
            code: Python code containing generate_test_cases(n, size='mixed') function
            num_cases: Number of test cases to generate
            timeout: Maximum execution time in seconds
            size: Test case size - 'small', 'medium', 'large', or 'mixed' (default)

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
        import inspect

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

            # Check if function accepts size parameter (backwards compatibility)
            sig = inspect.signature(generate_func)
            if 'size' in sig.parameters:
                test_cases = generate_func(num_cases, size=size)
            else:
                # Old function signature: generate_test_cases(n)
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

    @staticmethod
    def execute_generator_code_incrementally(code: str, num_cases: int = 10) -> List[str]:
        """
        Execute test case generator code one at a time, saving each to a temp file

        Args:
            code: Python code containing generate_test_cases(n) function
            num_cases: Number of test cases to generate

        Returns:
            List of file paths to generated test case files

        Raises:
            ValueError: If execution fails or code is unsafe
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

            # Generate test cases one by one
            generate_func = safe_globals['generate_test_cases']
            test_cases = []

            for i in range(num_cases):
                # Generate 1 test case at a time
                single_case = generate_func(1)

                if not isinstance(single_case, list) or len(single_case) == 0:
                    raise ValueError(f'generate_test_cases(1) must return a list with 1 element')

                # Take the first element
                test_case = single_case[0]

                if not isinstance(test_case, str):
                    raise ValueError(f'Test case {i} is not a string: {type(test_case)}')

                test_cases.append(test_case)

            return test_cases

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f'Error executing test case generator: {str(e)}')
