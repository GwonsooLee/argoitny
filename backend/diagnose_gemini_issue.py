#!/usr/bin/env python3
"""Diagnose Gemini API configuration issues"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

api_key = os.getenv('GEMINI_API_KEY')

print("=" * 80)
print("GEMINI API CONFIGURATION DIAGNOSIS")
print("=" * 80)

print(f"\n1. Environment File Location:")
print(f"   {env_path}")
print(f"   Exists: {env_path.exists()}")

print(f"\n2. API Key Status:")
if not api_key:
    print("   ERROR: GEMINI_API_KEY not found in environment")
    print(f"   Action: Add GEMINI_API_KEY to {env_path}")
elif api_key == 'your-gemini-api-key':
    print("   ERROR: GEMINI_API_KEY is set to placeholder value")
    print(f"   Action: Replace 'your-gemini-api-key' with your actual API key in {env_path}")
    print()
    print("   To get a Gemini API key:")
    print("   1. Visit: https://makersuite.google.com/app/apikey")
    print("   2. Click 'Create API key'")
    print("   3. Copy the generated key")
    print(f"   4. Edit {env_path} and replace the placeholder")
else:
    print(f"   OK: API key is configured (length: {len(api_key)} characters)")
    print(f"   Preview: {api_key[:10]}...{api_key[-4:]}")

print(f"\n3. Understanding the Error:")
print("   The error message indicates:")
print("   '404 models/gemini-1.5-flash is not found for API version v1beta'")
print()
print("   This error can occur because:")
print("   a) Invalid API key or placeholder value")
print("   b) Model name needs the correct format")
print("   c) API version compatibility issue")

print(f"\n4. Correct Model Name Format:")
print("   The google-generativeai SDK (v0.8.5) supports these formats:")
print("   - 'gemini-1.5-flash' (short name - recommended)")
print("   - 'gemini-1.5-pro' (short name)")
print("   - 'gemini-pro' (legacy)")
print()
print("   Do NOT use:")
print("   - 'models/gemini-1.5-flash' (this is the full path returned by list_models)")

print(f"\n5. Current gemini_service.py Configuration:")
try:
    service_path = Path(__file__).parent / 'api' / 'services' / 'gemini_service.py'
    if service_path.exists():
        with open(service_path) as f:
            content = f.read()
            if "GenerativeModel('gemini-1.5-flash')" in content:
                print("   OK: Using correct short name format 'gemini-1.5-flash'")
            elif "GenerativeModel('models/gemini-1.5-flash')" in content:
                print("   ERROR: Using full path format 'models/gemini-1.5-flash'")
                print("   Action: Change to short name 'gemini-1.5-flash'")
            else:
                print("   Model name format unclear - please check manually")
    else:
        print(f"   ERROR: Service file not found at {service_path}")
except Exception as e:
    print(f"   ERROR: Could not check service file: {e}")

print("\n" + "=" * 80)
print("RECOMMENDED ACTIONS:")
print("=" * 80)

if not api_key or api_key == 'your-gemini-api-key':
    print("\nSTEP 1: Configure your API key")
    print(f"  Edit: {env_path}")
    print("  Find the line: GEMINI_API_KEY=your-gemini-api-key")
    print("  Replace with: GEMINI_API_KEY=your_actual_api_key_here")
    print()
    print("  Get your API key from: https://makersuite.google.com/app/apikey")
    print()
    print("STEP 2: Run the model listing script")
    print("  python list_gemini_models.py")
    print()
    print("  This will show you all available models for your API key")
else:
    print("\nYour API key appears to be configured.")
    print("Next step: Run the model listing script to verify access")
    print()
    print("  python list_gemini_models.py")

print("\n")
