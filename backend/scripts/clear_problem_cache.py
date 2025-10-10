#!/usr/bin/env python
"""Clear problem-related caches"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache

# Clear caches
cache_keys = [
    "problem_drafts:all",
    "problem_registered:all"
]

for key in cache_keys:
    result = cache.delete(key)
    print(f"Cleared cache: {key} (result: {result})")

print("\nAll problem caches cleared!")
