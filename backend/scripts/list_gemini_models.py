#!/usr/bin/env python3
"""Script to list available Gemini models"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

api_key = os.getenv('GEMINI_API_KEY')

if not api_key or api_key == 'your-gemini-api-key':
    print("ERROR: GEMINI_API_KEY not configured in .env file")
    print(f"Please edit {env_path} and set a valid API key")
    sys.exit(1)

print(f"Using API key: {api_key[:10]}...{api_key[-4:]}")
print("\nConfiguring Gemini API...")

try:
    genai.configure(api_key=api_key)
    print("API configured successfully!\n")

    print("=" * 80)
    print("AVAILABLE GEMINI MODELS")
    print("=" * 80)

    models = genai.list_models()

    generate_content_models = []
    other_models = []

    for model in models:
        model_info = {
            'name': model.name,
            'display_name': model.display_name,
            'supported_methods': model.supported_generation_methods
        }

        if 'generateContent' in model.supported_generation_methods:
            generate_content_models.append(model_info)
        else:
            other_models.append(model_info)

    print("\nMODELS SUPPORTING generateContent (use these!):")
    print("-" * 80)
    for i, model_info in enumerate(generate_content_models, 1):
        print(f"\n{i}. {model_info['display_name']}")
        print(f"   Model Name: {model_info['name']}")
        print(f"   Supported Methods: {', '.join(model_info['supported_methods'])}")

    if other_models:
        print("\n\nOTHER MODELS (not suitable for generateContent):")
        print("-" * 80)
        for i, model_info in enumerate(other_models, 1):
            print(f"\n{i}. {model_info['display_name']}")
            print(f"   Model Name: {model_info['name']}")
            print(f"   Supported Methods: {', '.join(model_info['supported_methods'])}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    if generate_content_models:
        # Find the best model to use
        recommended = None

        # Prioritize flash models for speed and cost-effectiveness
        for model in generate_content_models:
            if 'flash' in model['name'].lower():
                recommended = model
                break

        if not recommended:
            recommended = generate_content_models[0]

        print(f"\nUse this model name in your code:")
        print(f"  {recommended['name']}")
        print(f"\nOr try the short name:")
        short_name = recommended['name'].replace('models/', '')
        print(f"  {short_name}")
    else:
        print("\nNo models supporting generateContent found!")
        print("This might indicate an API key permissions issue.")

    print("\n")

except Exception as e:
    print(f"\nERROR: {str(e)}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. API key doesn't have proper permissions")
    print("3. Network connectivity issues")
    print("4. API quota exceeded")
    sys.exit(1)
