"""Test script to list available Gemini models"""
import google.generativeai as genai
import os

# Get API key from environment or settings
api_key = os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("Available Gemini models:")
print("-" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Supported Methods: {model.supported_generation_methods}")
        print()
