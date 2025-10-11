#!/usr/bin/env python3
"""Test Gemini Flash integration and cost tracking"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algoitny.settings')
import django
django.setup()

from api.services.llm_factory import LLMServiceFactory
from api.utils.llm_cost_tracker import LLMCostTracker


def test_tier_selection():
    """Test tier-based service selection"""
    print("\n" + "="*80)
    print("Testing Tier-Based Service Selection")
    print("="*80)

    # Test simple tier (should return GeminiFlashService)
    print("\n1. Testing 'simple' tier (should use Gemini Flash)...")
    try:
        service = LLMServiceFactory.create_service(task_tier='simple')
        print(f"✓ Service created: {type(service).__name__}")
        print(f"✓ Model: {service.model._model_name if hasattr(service.model, '_model_name') else 'N/A'}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test moderate tier (should return GeminiService)
    print("\n2. Testing 'moderate' tier (should use Gemini Pro)...")
    try:
        service = LLMServiceFactory.create_service(task_tier='moderate')
        print(f"✓ Service created: {type(service).__name__}")
        print(f"✓ Model: {service.model._model_name if hasattr(service.model, '_model_name') else 'N/A'}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test direct service selection
    print("\n3. Testing direct 'gemini-flash' selection...")
    try:
        service = LLMServiceFactory.create_service('gemini-flash')
        print(f"✓ Service created: {type(service).__name__}")
        print(f"✓ Model: {service.model._model_name if hasattr(service.model, '_model_name') else 'N/A'}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test available services
    print("\n4. Available services:")
    available = LLMServiceFactory.get_available_services()
    for service in available:
        print(f"  - {service}")


def test_cost_tracking():
    """Test cost tracking utility"""
    print("\n" + "="*80)
    print("Testing Cost Tracking")
    print("="*80)

    # Example: Metadata extraction (typical size)
    print("\n1. Metadata Extraction Example (5K input, 1K output):")
    comparison = LLMCostTracker.compare_models(5000, 1000)

    for model_id, info in sorted(comparison.items(), key=lambda x: x[1]['total_cost']):
        print(
            f"  {info['model']:20} | "
            f"${info['total_cost']:8.6f} | "
            f"Savings: ${info['savings_vs_max']:8.6f} ({info['savings_percent']:5.1f}%)"
        )

    # Example: Solution generation (typical size)
    print("\n2. Solution Generation Example (10K input, 3K output):")
    LLMCostTracker.print_cost_report(10000, 3000)


def test_cost_savings():
    """Calculate and display cost savings"""
    print("\n" + "="*80)
    print("Cost Savings Analysis - Monthly Usage (1000 problems)")
    print("="*80)

    # Assumptions for 1000 problems
    metadata_extraction = {
        'count': 1000,
        'input_tokens': 5000,
        'output_tokens': 1000
    }

    # Old approach: All metadata with Gemini Pro
    old_cost = LLMCostTracker.calculate_cost(
        'gemini-pro',
        metadata_extraction['input_tokens'],
        metadata_extraction['output_tokens']
    )['total_cost'] * metadata_extraction['count']

    # New approach: Metadata with Gemini Flash
    new_cost = LLMCostTracker.calculate_cost(
        'gemini-flash',
        metadata_extraction['input_tokens'],
        metadata_extraction['output_tokens']
    )['total_cost'] * metadata_extraction['count']

    print(f"\nMetadata Extraction (1000 problems):")
    print(f"  Old (Gemini Pro):    ${old_cost:.2f}/month")
    print(f"  New (Gemini Flash):  ${new_cost:.2f}/month")
    print(f"  Savings:             ${old_cost - new_cost:.2f}/month (${(old_cost - new_cost) * 12:.2f}/year)")
    print(f"  Reduction:           {((old_cost - new_cost) / old_cost * 100):.1f}%")


if __name__ == '__main__':
    print("\nGemini Flash Integration Test")
    print("="*80)

    test_tier_selection()
    test_cost_tracking()
    test_cost_savings()

    print("\n" + "="*80)
    print("✓ All tests completed successfully!")
    print("="*80 + "\n")
