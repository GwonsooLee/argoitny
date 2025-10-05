# Gemini API Setup and Troubleshooting Guide

## Current Issue

You're experiencing a `404` error when trying to use the Gemini API:

```
404 models/gemini-1.5-flash is not found for API version v1beta
```

## Root Cause

**The GEMINI_API_KEY in your `.env` file is set to a placeholder value** (`your-gemini-api-key`), which causes the API to reject requests.

## Solution

### Step 1: Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API key"** or **"Get API key"**
4. Copy the generated API key (it will look something like: `AIzaSyC-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### Step 2: Configure Your API Key

Edit `/Users/gwonsoolee/algoitny/backend/.env`:

```bash
# Replace this line:
GEMINI_API_KEY=your-gemini-api-key

# With your actual API key:
GEMINI_API_KEY=AIzaSyC-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Verify Your Configuration

Run the model listing script to verify your API key works and see available models:

```bash
cd /Users/gwonsoolee/algoitny/backend
python list_gemini_models.py
```

This will display all models available to your API key.

## Available Gemini Models (as of January 2025)

Based on the Google Generative AI SDK v0.8.5, these are the common models you can use:

### Recommended Models

1. **gemini-1.5-flash** (Currently used in your code)
   - Best for: Fast responses, cost-effective
   - Use case: General tasks, code generation, test case generation
   - Speed: Very fast
   - Cost: Lower

2. **gemini-1.5-pro**
   - Best for: Complex reasoning, longer context
   - Use case: Advanced problem solving, detailed analysis
   - Speed: Moderate
   - Cost: Higher

3. **gemini-pro** (Legacy)
   - Best for: General purpose tasks
   - Note: Being superseded by gemini-1.5-flash
   - Speed: Fast
   - Cost: Moderate

### Model Name Format

**CORRECT** (short name):
```python
genai.GenerativeModel('gemini-1.5-flash')
```

**INCORRECT** (full path - will cause errors):
```python
genai.GenerativeModel('models/gemini-1.5-flash')
```

## Your Current Configuration

Your `gemini_service.py` is correctly configured to use:
- Model: `gemini-1.5-flash` ✓
- Format: Short name ✓

The only issue is the API key configuration.

## Testing After Configuration

Once you've set up your API key, test the service:

```bash
cd /Users/gwonsoolee/algoitny/backend
python manage.py shell
```

Then in the Django shell:

```python
from api.services.gemini_service import GeminiService

service = GeminiService()

# Test with sample data
problem_info = {
    'platform': 'leetcode',
    'problem_id': '1',
    'title': 'Two Sum',
    'solution_code': 'def twoSum(nums, target): return []',
    'language': 'python',
    'constraints': 'n <= 1000'
}

test_cases = service.generate_test_cases(problem_info)
print(f"Generated {len(test_cases)} test cases")
```

## Common Issues and Solutions

### Issue: "Invalid API key"
- **Cause**: API key is incorrect or has been revoked
- **Solution**: Generate a new API key from Google AI Studio

### Issue: "Quota exceeded"
- **Cause**: You've exceeded the free tier limits
- **Solution**:
  - Wait for quota to reset (usually daily)
  - Enable billing in Google Cloud Console for higher limits

### Issue: "Model not found"
- **Cause**: Using incorrect model name format or model doesn't exist
- **Solution**:
  - Use short name format (e.g., `gemini-1.5-flash`)
  - Run `list_gemini_models.py` to see available models

### Issue: "Permission denied"
- **Cause**: API key doesn't have proper permissions
- **Solution**: Regenerate the API key with correct permissions

## API Rate Limits (Free Tier)

- **Requests per minute**: 60
- **Requests per day**: 1,500
- **Tokens per minute**: 32,000

For production use, consider:
- Implementing request caching
- Rate limiting on your backend
- Upgrading to a paid plan for higher limits

## SDK Version

Your project uses:
- **Package**: `google-generativeai`
- **Version**: `>= 0.3.0` (currently installed: 0.8.5)
- **Python**: 3.8+

## Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Python SDK Reference](https://ai.google.dev/api/python/google/generativeai)
- [API Pricing](https://ai.google.dev/pricing)
- [Get API Key](https://makersuite.google.com/app/apikey)

## Next Steps

1. Set up your API key in `.env`
2. Run `python list_gemini_models.py` to verify
3. Test the service using the Django shell example above
4. If everything works, your test case generation should work!

---

**Need Help?**

If you continue to experience issues after setting up your API key, run:
```bash
python diagnose_gemini_issue.py
```

This will provide detailed diagnostics about your configuration.
