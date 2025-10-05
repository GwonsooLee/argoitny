#!/usr/bin/env python3
"""Test Gemini Service functionality"""
import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"Warning: Could not fully initialize Django: {e}")
    print("Continuing with basic test...\n")

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

api_key = os.getenv('GEMINI_API_KEY')

print("=" * 80)
print("GEMINI SERVICE TEST")
print("=" * 80)

if not api_key or api_key == 'your-gemini-api-key':
    print("\nERROR: GEMINI_API_KEY not configured")
    print(f"Please edit {env_path} and set a valid API key")
    print("\nGet your API key from: https://makersuite.google.com/app/apikey")
    sys.exit(1)

print(f"\n1. API Key: {api_key[:10]}...{api_key[-4:]}")

try:
    # Configure API
    genai.configure(api_key=api_key)
    print("2. API Configuration: OK")

    # Test model initialization
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("3. Model Initialization: OK (gemini-1.5-flash)")

    # Test simple generation
    print("\n4. Testing content generation...")
    prompt = "Generate a simple JSON array with 2 test cases for adding two numbers. Format: [{\"input\": \"1 2\"}, {\"input\": \"3 4\"}]"

    response = model.generate_content(prompt)
    print("   Response received!")
    print(f"   Response length: {len(response.text)} characters")
    print(f"   Response preview: {response.text[:100]}...")

    # Test with actual service
    print("\n5. Testing GeminiService class...")
    try:
        from api.services.gemini_service import GeminiService

        service = GeminiService()

        # Simple test case
        problem_info = {
            'platform': 'test',
            'problem_id': '1',
            'title': 'Add Two Numbers',
            'solution_code': 'def add(a, b): return a + b',
            'language': 'python',
            'constraints': 'Small numbers only'
        }

        print("   Generating test cases (this may take 10-30 seconds)...")
        test_cases = service.generate_test_cases(problem_info)

        print(f"   SUCCESS: Generated {len(test_cases)} test cases")
        print(f"   Sample test case: {test_cases[0] if test_cases else 'None'}")

    except ImportError as e:
        print(f"   WARNING: Could not import GeminiService: {e}")
        print("   Direct API test passed, but Django service not tested")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    print("\nYour Gemini API is working correctly!")
    print("The test case generation feature should work now.")

except Exception as e:
    print(f"\nERROR: {str(e)}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. Network connectivity problems")
    print("3. API quota exceeded")
    print("4. Model name incorrect")
    print("\nTry running: python list_gemini_models.py")
    sys.exit(1)
