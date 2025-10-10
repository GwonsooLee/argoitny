#!/usr/bin/env python
"""Check specific problem in DynamoDB"""
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.repositories import ProblemRepository

# Get the problem using repository
repo = ProblemRepository()
problem = repo.get_problem(platform='codeforces', problem_id='2149G')

if problem:
    print("Found problem:")
    print(f"Platform: {problem.get('platform')}")
    print(f"Problem ID: {problem.get('problem_id')}")
    print(f"Title: {problem.get('title')}")
    print(f"is_completed: {problem.get('is_completed')}")
    print(f"\nFull problem data:")
    print(json.dumps(problem, indent=2, default=str))
    print(f"\nMetadata:")
    metadata = problem.get('metadata', {})
    print(json.dumps(metadata, indent=2, default=str))
    print(f"\nneeds_review in metadata: {metadata.get('needs_review', False)}")
else:
    print("Problem not found!")
