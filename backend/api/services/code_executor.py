"""Code Execution Service"""
import subprocess
import tempfile
import os
from pathlib import Path
from django.conf import settings


class CodeExecutor:
    """Execute code in various languages"""

    SUPPORTED_LANGUAGES = ['python', 'python3', 'javascript', 'node', 'cpp', 'c++', 'java']

    @staticmethod
    def execute(code, language, input_data):
        """
        Execute code with given input

        Args:
            code: Source code string
            language: Programming language
            input_data: Input string for the program

        Returns:
            dict: {
                'output': str,
                'error': str,
                'success': bool
            }
        """
        language = language.lower()

        if language not in CodeExecutor.SUPPORTED_LANGUAGES:
            return {
                'output': '',
                'error': f'Unsupported language: {language}',
                'success': False
            }

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                if language in ['python', 'python3']:
                    return CodeExecutor._execute_python(code, input_data, temp_path)
                elif language in ['javascript', 'node']:
                    return CodeExecutor._execute_javascript(code, input_data, temp_path)
                elif language in ['cpp', 'c++']:
                    return CodeExecutor._execute_cpp(code, input_data, temp_path)
                elif language == 'java':
                    return CodeExecutor._execute_java(code, input_data, temp_path)
            except Exception as e:
                return {
                    'output': '',
                    'error': str(e),
                    'success': False
                }

    @staticmethod
    def _execute_python(code, input_data, temp_path):
        """Execute Python code"""
        file_path = temp_path / 'solution.py'
        file_path.write_text(code)

        result = subprocess.run(
            ['python3', str(file_path)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT
        )

        return {
            'output': result.stdout,
            'error': result.stderr,
            'success': result.returncode == 0
        }

    @staticmethod
    def _execute_javascript(code, input_data, temp_path):
        """Execute JavaScript code"""
        file_path = temp_path / 'solution.js'
        file_path.write_text(code)

        result = subprocess.run(
            ['node', str(file_path)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT
        )

        return {
            'output': result.stdout,
            'error': result.stderr,
            'success': result.returncode == 0
        }

    @staticmethod
    def _execute_cpp(code, input_data, temp_path):
        """Execute C++ code"""
        source_path = temp_path / 'solution.cpp'
        exec_path = temp_path / 'solution'

        source_path.write_text(code)

        # Compile
        compile_result = subprocess.run(
            ['g++', str(source_path), '-o', str(exec_path)],
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT
        )

        if compile_result.returncode != 0:
            return {
                'output': '',
                'error': compile_result.stderr,
                'success': False
            }

        # Execute
        result = subprocess.run(
            [str(exec_path)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT
        )

        return {
            'output': result.stdout,
            'error': result.stderr,
            'success': result.returncode == 0
        }

    @staticmethod
    def _execute_java(code, input_data, temp_path):
        """Execute Java code"""
        import re

        # Extract class name from code
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        if not class_match:
            return {
                'output': '',
                'error': 'No public class found in code',
                'success': False
            }

        class_name = class_match.group(1)
        source_path = temp_path / f'{class_name}.java'

        source_path.write_text(code)

        # Compile
        compile_result = subprocess.run(
            ['javac', str(source_path)],
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
            cwd=str(temp_path)
        )

        if compile_result.returncode != 0:
            return {
                'output': '',
                'error': compile_result.stderr,
                'success': False
            }

        # Execute
        result = subprocess.run(
            ['java', class_name],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
            cwd=str(temp_path)
        )

        return {
            'output': result.stdout,
            'error': result.stderr,
            'success': result.returncode == 0
        }
