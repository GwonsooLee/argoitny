"""Async Code Execution Service using asyncio subprocess"""
import asyncio
import tempfile
import os
from pathlib import Path
from django.conf import settings


class AsyncCodeExecutor:
    """Execute code in various languages asynchronously"""

    SUPPORTED_LANGUAGES = ['python', 'python3', 'javascript', 'node', 'cpp', 'c++', 'java']

    @staticmethod
    async def execute(code, language, input_data):
        """
        Execute code with given input (async)

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

        if language not in AsyncCodeExecutor.SUPPORTED_LANGUAGES:
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
                    return await AsyncCodeExecutor._execute_python(code, input_data, temp_path)
                elif language in ['javascript', 'node']:
                    return await AsyncCodeExecutor._execute_javascript(code, input_data, temp_path)
                elif language in ['cpp', 'c++']:
                    return await AsyncCodeExecutor._execute_cpp(code, input_data, temp_path)
                elif language == 'java':
                    return await AsyncCodeExecutor._execute_java(code, input_data, temp_path)
            except Exception as e:
                return {
                    'output': '',
                    'error': str(e),
                    'success': False
                }

    @staticmethod
    async def _execute_python(code, input_data, temp_path):
        """Execute Python code (async)"""
        file_path = temp_path / 'solution.py'
        file_path.write_text(code)

        process = await asyncio.create_subprocess_exec(
            'python3', str(file_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode()),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                'output': '',
                'error': 'Execution timeout',
                'success': False
            }

        return {
            'output': stdout.decode(),
            'error': stderr.decode(),
            'success': process.returncode == 0
        }

    @staticmethod
    async def _execute_javascript(code, input_data, temp_path):
        """Execute JavaScript code (async)"""
        file_path = temp_path / 'solution.js'
        file_path.write_text(code)

        process = await asyncio.create_subprocess_exec(
            'node', str(file_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode()),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                'output': '',
                'error': 'Execution timeout',
                'success': False
            }

        return {
            'output': stdout.decode(),
            'error': stderr.decode(),
            'success': process.returncode == 0
        }

    @staticmethod
    async def _execute_cpp(code, input_data, temp_path):
        """Execute C++ code (async)"""
        source_path = temp_path / 'solution.cpp'
        exec_path = temp_path / 'solution'

        source_path.write_text(code)

        # Compile
        compile_process = await asyncio.create_subprocess_exec(
            'g++', str(source_path), '-o', str(exec_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            compile_stdout, compile_stderr = await asyncio.wait_for(
                compile_process.communicate(),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            compile_process.kill()
            await compile_process.wait()
            return {
                'output': '',
                'error': 'Compilation timeout',
                'success': False
            }

        if compile_process.returncode != 0:
            return {
                'output': '',
                'error': compile_stderr.decode(),
                'success': False
            }

        # Execute
        exec_process = await asyncio.create_subprocess_exec(
            str(exec_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                exec_process.communicate(input=input_data.encode()),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            exec_process.kill()
            await exec_process.wait()
            return {
                'output': '',
                'error': 'Execution timeout',
                'success': False
            }

        return {
            'output': stdout.decode(),
            'error': stderr.decode(),
            'success': exec_process.returncode == 0
        }

    @staticmethod
    async def _execute_java(code, input_data, temp_path):
        """Execute Java code (async)"""
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
        compile_process = await asyncio.create_subprocess_exec(
            'javac', str(source_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(temp_path)
        )

        try:
            compile_stdout, compile_stderr = await asyncio.wait_for(
                compile_process.communicate(),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            compile_process.kill()
            await compile_process.wait()
            return {
                'output': '',
                'error': 'Compilation timeout',
                'success': False
            }

        if compile_process.returncode != 0:
            return {
                'output': '',
                'error': compile_stderr.decode(),
                'success': False
            }

        # Execute
        exec_process = await asyncio.create_subprocess_exec(
            'java', class_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(temp_path)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                exec_process.communicate(input=input_data.encode()),
                timeout=settings.CODE_EXECUTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            exec_process.kill()
            await exec_process.wait()
            return {
                'output': '',
                'error': 'Execution timeout',
                'success': False
            }

        return {
            'output': stdout.decode(),
            'error': stderr.decode(),
            'success': exec_process.returncode == 0
        }
