#!/usr/bin/env python
"""
Test script to debug JSON parsing issues in Gemini responses.
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.services.gemini_service import GeminiService

def test_problem_extraction():
    """Test extracting problem metadata from a URL that was failing."""
    service = GeminiService()

    test_url = "https://codeforces.com/contest/1359/problem/C"

    print(f"Testing problem extraction from: {test_url}")
    print("-" * 80)

    try:
        result = service.extract_problem_metadata_from_url(test_url)
        print("✅ Success!")
        print(f"Title: {result.get('title')}")
        print(f"Tags: {result.get('tags')}")
        print(f"Samples: {len(result.get('samples', []))} samples")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_problem_extraction()
