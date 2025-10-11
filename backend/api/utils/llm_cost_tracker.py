"""LLM Cost Tracking Utility

Track and monitor LLM API costs across different providers and models.
Helps optimize spending by providing visibility into usage patterns.
"""
import logging
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMCostTracker:
    """
    Track LLM costs for different models and tasks

    Cost structure (per 1M tokens):
    - Gemini Flash: $0.075 input / $0.30 output
    - Gemini Pro: $1.25 input / $5.00 output
    - GPT-4o: $2.50 input / $10.00 output
    - GPT-5: $10.00 input / $40.00 output
    """

    # Cost per 1M tokens (input/output)
    COSTS = {
        'gemini-flash': {
            'input': 0.075,
            'output': 0.30,
            'name': 'Gemini 1.5 Flash'
        },
        'gemini-pro': {
            'input': 1.25,
            'output': 5.00,
            'name': 'Gemini 2.5 Pro'
        },
        'gpt-4o': {
            'input': 2.50,
            'output': 10.00,
            'name': 'GPT-4o'
        },
        'gpt-5': {
            'input': 10.00,
            'output': 40.00,
            'name': 'GPT-5'
        },
    }

    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """
        Calculate cost for LLM API call

        Args:
            model: Model name ('gemini-flash', 'gemini-pro', 'gpt-4o', 'gpt-5')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            dict: {
                'input_cost': float,
                'output_cost': float,
                'total_cost': float,
                'model': str
            }
        """
        if model not in cls.COSTS:
            logger.warning(f"Unknown model '{model}', cost tracking skipped")
            return {
                'input_cost': 0.0,
                'output_cost': 0.0,
                'total_cost': 0.0,
                'model': model
            }

        costs = cls.COSTS[model]

        # Cost per million tokens
        input_cost = (input_tokens / 1_000_000) * costs['input']
        output_cost = (output_tokens / 1_000_000) * costs['output']

        return {
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(input_cost + output_cost, 6),
            'model': costs['name'],
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }

    @classmethod
    def log_cost(cls, model: str, input_tokens: int, output_tokens: int, task: str = 'unknown'):
        """
        Calculate and log cost for LLM API call

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            task: Task description (e.g., 'metadata_extraction', 'solution_generation')
        """
        cost_info = cls.calculate_cost(model, input_tokens, output_tokens)

        logger.info(
            f"[LLM Cost] Task: {task} | "
            f"Model: {cost_info['model']} | "
            f"Tokens: {input_tokens:,} in / {output_tokens:,} out | "
            f"Cost: ${cost_info['input_cost']:.6f} + ${cost_info['output_cost']:.6f} = "
            f"${cost_info['total_cost']:.6f}"
        )

        return cost_info

    @classmethod
    def compare_models(cls, input_tokens: int, output_tokens: int) -> Dict[str, Dict]:
        """
        Compare costs across all models for given token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            dict: Model comparison with costs and savings
        """
        comparison = {}
        costs_list = []

        for model_id in cls.COSTS:
            cost = cls.calculate_cost(model_id, input_tokens, output_tokens)
            comparison[model_id] = cost
            costs_list.append(cost['total_cost'])

        # Calculate savings vs most expensive
        max_cost = max(costs_list)
        for model_id, info in comparison.items():
            info['savings_vs_max'] = round(max_cost - info['total_cost'], 6)
            info['savings_percent'] = round(
                ((max_cost - info['total_cost']) / max_cost * 100) if max_cost > 0 else 0,
                1
            )

        return comparison

    @classmethod
    def print_cost_report(cls, input_tokens: int, output_tokens: int):
        """
        Print a formatted cost comparison report

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        comparison = cls.compare_models(input_tokens, output_tokens)

        print("\n" + "="*80)
        print(f"LLM Cost Comparison ({input_tokens:,} input / {output_tokens:,} output tokens)")
        print("="*80)

        # Sort by total cost
        sorted_models = sorted(
            comparison.items(),
            key=lambda x: x[1]['total_cost']
        )

        for model_id, info in sorted_models:
            print(
                f"{info['model']:20} | "
                f"${info['total_cost']:8.6f} | "
                f"Savings: ${info['savings_vs_max']:8.6f} ({info['savings_percent']:5.1f}%)"
            )

        print("="*80 + "\n")


# Convenience function
def track_llm_cost(model: str, input_tokens: int, output_tokens: int, task: str = 'unknown'):
    """
    Track LLM cost (convenience wrapper)

    Usage:
        from api.utils.llm_cost_tracker import track_llm_cost

        track_llm_cost('gemini-flash', 1000, 500, 'metadata_extraction')
    """
    return LLMCostTracker.log_cost(model, input_tokens, output_tokens, task)
