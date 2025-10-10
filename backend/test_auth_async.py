#!/usr/bin/env python
"""
Test script to verify auth.py async conversion

This script checks that all view methods in auth.py are properly converted to async.

Usage:
    python test_auth_async.py
"""

import ast
import sys
from pathlib import Path


def check_auth_async():
    """Check if auth.py has been properly converted to async"""
    auth_file = Path(__file__).parent / 'api' / 'views' / 'auth.py'

    if not auth_file.exists():
        print(f"✗ File not found: {auth_file}")
        return False

    with open(auth_file, 'r') as f:
        content = f.read()
        tree = ast.parse(content)

    results = {
        'imports': {},
        'views': {},
        'methods': {},
        'await_count': 0
    }

    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'adrf.views':
                results['imports']['adrf'] = True
            if node.module == 'asgiref.sync':
                for alias in node.names:
                    if alias.name == 'sync_to_async':
                        results['imports']['sync_to_async'] = True
            if node.module and 'async_repositories' in node.module:
                results['imports']['async_repositories'] = True
            if node.module and 'async_client' in node.module:
                results['imports']['async_client'] = True

    # Check view classes and methods
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if 'View' in node.name:
                results['views'][node.name] = {
                    'methods': [],
                    'async_methods': []
                }
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        results['views'][node.name]['methods'].append(item.name)
                        if isinstance(item, ast.AsyncFunctionDef):
                            results['views'][node.name]['async_methods'].append(item.name)
                            results['methods'][f'{node.name}.{item.name}'] = 'async'
                        else:
                            results['methods'][f'{node.name}.{item.name}'] = 'sync'

    # Count await expressions
    results['await_count'] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Await))

    # Print results
    print("=" * 70)
    print("AUTH.PY ASYNC CONVERSION VERIFICATION")
    print("=" * 70)

    # Check imports
    print("\n1. IMPORTS")
    print("-" * 70)
    checks = [
        ('adrf.views', 'adrf'),
        ('sync_to_async', 'sync_to_async'),
        ('AsyncRepositories', 'async_repositories'),
        ('AsyncDynamoDBClient', 'async_client')
    ]

    all_imports_ok = True
    for name, key in checks:
        if results['imports'].get(key):
            print(f"  ✓ {name} imported")
        else:
            print(f"  ✗ {name} NOT imported")
            all_imports_ok = False

    # Check views
    print("\n2. VIEW CLASSES")
    print("-" * 70)
    expected_views = ['GoogleLoginView', 'TokenRefreshView', 'LogoutView', 'AvailablePlansView']

    all_views_ok = True
    for view_name in expected_views:
        if view_name in results['views']:
            async_methods = results['views'][view_name]['async_methods']
            if async_methods:
                print(f"  ✓ {view_name}: {len(async_methods)} async method(s)")
            else:
                print(f"  ✗ {view_name}: NO async methods found")
                all_views_ok = False
        else:
            print(f"  ✗ {view_name}: NOT found")
            all_views_ok = False

    # Check methods
    print("\n3. VIEW METHODS")
    print("-" * 70)
    expected_methods = [
        'GoogleLoginView.post',
        'TokenRefreshView.post',
        'LogoutView.post',
        'AvailablePlansView.get'
    ]

    all_methods_ok = True
    for method in expected_methods:
        if method in results['methods']:
            method_type = results['methods'][method]
            if method_type == 'async':
                print(f"  ✓ {method}: async def")
            else:
                print(f"  ✗ {method}: def (should be async def)")
                all_methods_ok = False
        else:
            print(f"  ✗ {method}: NOT found")
            all_methods_ok = False

    # Check await count
    print("\n4. ASYNC OPERATIONS")
    print("-" * 70)
    min_expected_awaits = 8  # At least 8 await expressions expected
    if results['await_count'] >= min_expected_awaits:
        print(f"  ✓ Found {results['await_count']} await expressions (expected >= {min_expected_awaits})")
        awaits_ok = True
    else:
        print(f"  ✗ Found only {results['await_count']} await expressions (expected >= {min_expected_awaits})")
        awaits_ok = False

    # Final verdict
    print("\n5. SUMMARY")
    print("-" * 70)
    all_ok = all_imports_ok and all_views_ok and all_methods_ok and awaits_ok

    if all_ok:
        print("  ✓ ALL CHECKS PASSED - auth.py is properly converted to async!")
    else:
        print("  ✗ SOME CHECKS FAILED - review the output above")
        if not all_imports_ok:
            print("    - Missing required imports")
        if not all_views_ok:
            print("    - Some views are not async")
        if not all_methods_ok:
            print("    - Some methods are not async")
        if not awaits_ok:
            print("    - Insufficient await expressions")

    print("=" * 70)

    return all_ok


def main():
    success = check_auth_async()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
