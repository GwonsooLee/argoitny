def generate_test_cases(n):
    import random
    test_cases = []

    # Calculate distribution: 50% small, 30% medium, 20% large
    num_small = n // 2
    num_medium = (n * 3) // 10
    num_large = n - num_small - num_medium

    # SMALL cases (50%)
    for _ in range(num_small):
        t = random.randint(1, 3)  # Few test cases
        cases = []
        for _ in range(t):
            arr_size = random.randint(1, 10)  # Small array
            arr = [random.randint(1, 100) for _ in range(arr_size)]
            cases.append(f"{arr_size}\n{' '.join(map(str, arr))}")
        test_cases.append(f"{t}\n{chr(10).join(cases)}")

    # MEDIUM cases (30%)
    for _ in range(num_medium):
        t = random.randint(5, 50)  # Moderate number of test cases
        cases = []
        for _ in range(t):
            arr_size = random.randint(100, 1000)  # Medium array
            arr = [random.randint(1, 10**6) for _ in range(arr_size)]
            cases.append(f"{arr_size}\n{' '.join(map(str, arr))}")
        test_cases.append(f"{t}\n{chr(10).join(cases)}")

    # LARGE cases (20%) - USE MAXIMUM CONSTRAINT VALUES
    for _ in range(num_large):
        # Use MAXIMUM t value from constraints
        t = random.randint(800, 1000)  # t <= 1000, so use close to max
        cases = []
        for _ in range(t):
            # Use MAXIMUM n and a[i] values
            arr_size = random.randint(90000, 100000)  # n <= 10^5
            arr = [random.randint(10**8, 10**9) for _ in range(arr_size)]  # a[i] <= 10^9
            cases.append(f"{arr_size}\n{' '.join(map(str, arr))}")
        test_cases.append(f"{t}\n{chr(10).join(cases)}")

    random.shuffle(test_cases)
    return test_cases

print(generate_test_cases(1))
