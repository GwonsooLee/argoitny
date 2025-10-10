#!/usr/bin/env python
"""Check needs_review field in DynamoDB"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.repositories import ProblemRepository

# Get problems
repo = ProblemRepository()

# Check drafts
print("=" * 80)
print("DRAFT PROBLEMS:")
print("=" * 80)
drafts, _ = repo.list_draft_problems(limit=10)
for problem in drafts:
    needs_review = problem.get('metadata', {}).get('needs_review', False)
    print(f"Platform: {problem['platform']}, ID: {problem['problem_id']}")
    print(f"  Title: {problem['title']}")
    print(f"  needs_review: {needs_review}")
    print(f"  metadata: {problem.get('metadata', {})}")
    print()

# Check completed
print("=" * 80)
print("COMPLETED PROBLEMS:")
print("=" * 80)
completed, _ = repo.list_completed_problems(limit=10)
for problem in completed:
    needs_review = problem.get('metadata', {}).get('needs_review', False)
    print(f"Platform: {problem['platform']}, ID: {problem['problem_id']}")
    print(f"  Title: {problem['title']}")
    print(f"  needs_review: {needs_review}")
    print(f"  metadata: {problem.get('metadata', {})}")
    print()
