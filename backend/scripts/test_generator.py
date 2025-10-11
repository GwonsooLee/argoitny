#!/usr/bin/env python
"""Test the generator code to debug subprocess errors"""
import json
import sys

# Safe builtins
safe_builtins = {
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
    'filter': filter, 'float': float, 'format': format, 'hex': hex,
    'int': int, 'isinstance': isinstance, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'oct': oct, 'ord': ord,
    'pow': pow, 'range': range, 'repr': repr, 'reversed': reversed,
    'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
    'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
    'True': True, 'False': False, 'None': None,
}

safe_globals = {
    '__builtins__': safe_builtins,
}

# Import safe modules
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

# Generator code from user
generator_code = '''
def generate_test_cases(n, size='mixed'):
    import random

    def _generate_one_case(n_val, tree_type, seq_type):
        """Helper function to generate a single test case string."""
        if n_val == 1:
            return "1\\n1"

        # 1. Generate tree edges (rooted at 1, as per problem)
        edges = []
        if tree_type == 'line':
            # Tree is a path: 1-2-3-...-n
            for i in range(1, n_val):
                edges.append((i, i + 1))
        elif tree_type == 'star':
            # Node 1 is the center, connected to all others
            for i in range(2, n_val + 1):
                edges.append((1, i))
        else:  # 'random'
            # Generate a random tree by connecting each node i > 1 to a random node j < i
            # This guarantees a connected tree rooted at 1.
            for i in range(2, n_val + 1):
                parent = random.randint(1, i - 1)
                edges.append((i, parent))

        adj = {i: [] for i in range(1, n_val + 1)}
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)

        # 2. Generate the sequence 'a'
        a = []
        if seq_type == 'yes' or seq_type == 'no_order':
            # Generate a valid BFS sequence first for both 'yes' and 'no_order' cases.
            q = [1]
            visited = {1}
            head = 0
            while head < len(q):
                u = q[head]
                head += 1
                a.append(u)

                unvisited_neighbors = [v for v in adj[u] if v not in visited]
                random.shuffle(unvisited_neighbors)

                for v in unvisited_neighbors:
                    visited.add(v)
                    q.append(v)

            if seq_type == 'no_order' and n_val > 2:
                # To make it an invalid sequence, swap two elements after the root.
                # This is highly likely to break the BFS parent-child level structure.
                i, j = random.sample(range(1, n_val), 2)
                a[i], a[j] = a[j], a[i]

        elif seq_type == 'no_start':
            # Generate a permutation that doesn't start with 1 (guaranteed 'No').
            a = list(range(1, n_val + 1))
            random.shuffle(a)
            if a[0] == 1 and n_val > 1:
                idx_to_swap = random.randint(1, n_val - 1)
                a[0], a[idx_to_swap] = a[idx_to_swap], a[0]

        # 3. Format the output string
        random.shuffle(edges)
        edge_strs = [f"{u} {v}" for u, v in edges]

        output_parts = [str(n_val)]
        output_parts.extend(edge_strs)
        output_parts.append(' '.join(map(str, a)))
        return '\\n'.join(output_parts)

    test_cases = []

    # Define configurations for different sizes and types of test cases
    small_configs = [
        {'n_range': (1, 1), 'params': {'tree': 'random', 'seq': 'yes'}},
        {'n_range': (2, 2), 'params': {'tree': 'random', 'seq': 'yes'}},
        {'n_range': (2, 2), 'params': {'tree': 'random', 'seq': 'no_start'}},
        {'n_range': (3, 20), 'params': {'tree': 'line', 'seq': 'yes'}},
        {'n_range': (3, 20), 'params': {'tree': 'line', 'seq': 'no_order'}},
        {'n_range': (3, 20), 'params': {'tree': 'star', 'seq': 'yes'}},
        {'n_range': (3, 20), 'params': {'tree': 'random', 'seq': 'yes'}},
        {'n_range': (3, 20), 'params': {'tree': 'random', 'seq': 'no_order'}},
        {'n_range': (3, 20), 'params': {'tree': 'random', 'seq': 'no_start'}},
    ]

    medium_configs = [
        {'n_range': (200, 2000), 'params': {'tree': 'random', 'seq': 'yes'}},
        {'n_range': (200, 2000), 'params': {'tree': 'random', 'seq': 'no_order'}},
        {'n_range': (200, 2000), 'params': {'tree': 'random', 'seq': 'no_start'}},
        {'n_range': (200, 2000), 'params': {'tree': 'line', 'seq': 'no_order'}},
        {'n_range': (200, 2000), 'params': {'tree': 'star', 'seq': 'yes'}},
    ]

    large_configs = [
        {'n_range': (190000, 200000), 'params': {'tree': 'random', 'seq': 'yes'}},
        {'n_range': (190000, 200000), 'params': {'tree': 'random', 'seq': 'no_order'}},
        {'n_range': (190000, 200000), 'params': {'tree': 'random', 'seq': 'no_start'}},
        {'n_range': (190000, 200000), 'params': {'tree': 'line', 'seq': 'no_order'}},
        {'n_range': (190000, 200000), 'params': {'tree': 'star', 'seq': 'yes'}},
    ]

    if size == 'small':
        for _ in range(n):
            config = random.choice(small_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))
    elif size == 'medium':
        for _ in range(n):
            config = random.choice(medium_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))
    elif size == 'large':
        for _ in range(n):
            config = random.choice(large_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))
    else:  # 'mixed'
        num_small = n // 2
        num_medium = (n * 3) // 10
        num_large = n - num_small - num_medium

        for _ in range(num_small):
            config = random.choice(small_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))

        for _ in range(num_medium):
            config = random.choice(medium_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))

        for _ in range(num_large):
            config = random.choice(large_configs)
            n_val = random.randint(config['n_range'][0], config['n_range'][1])
            test_cases.append(_generate_one_case(n_val, **config['params']))

    random.shuffle(test_cases)
    return test_cases
'''

# Execute generator code
exec(generator_code, safe_globals)

# Generate test case
if 'generate_test_cases' not in safe_globals:
    print(json.dumps({"error": "generate_test_cases function not found"}))
    sys.exit(1)

try:
    # Test with size parameter
    import inspect
    sig = inspect.signature(safe_globals['generate_test_cases'])
    if 'size' in sig.parameters:
        result = safe_globals['generate_test_cases'](1, size="small")
    else:
        # Fallback to old signature
        result = safe_globals['generate_test_cases'](1)

    if not isinstance(result, list) or len(result) == 0:
        print(json.dumps({"error": "generate_test_cases(1) must return a list with 1 element"}))
        sys.exit(1)

    test_case = result[0]
    if not isinstance(test_case, str):
        print(json.dumps({"error": f"Test case is not a string: {type(test_case)}"}))
        sys.exit(1)

    print(json.dumps({"test_case": test_case, "length": len(test_case)}))
except Exception as e:
    import traceback
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
    sys.exit(1)
