"""LLM Model Selection Views"""
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)


class AvailableModelsView(APIView):
    """Get list of available LLM models with their details"""
    permission_classes = [AllowAny]

    async def get(self, request):
        """
        Get list of available LLM models for problem extraction/solution generation

        Returns:
            {
                "models": [
                    {
                        "id": "gpt-5",
                        "name": "GPT-5",
                        "provider": "OpenAI",
                        "description": "Most powerful model for complex problems",
                        "tier": "complex",
                        "cost": {
                            "input": 10.00,
                            "output": 40.00,
                            "unit": "per 1M tokens"
                        },
                        "features": {
                            "reasoning_effort": ["low", "medium", "high"],
                            "max_output_tokens": 32768
                        },
                        "recommended_for": ["Hard problems (2000+ rating)", "Complex algorithms"],
                        "available": true
                    },
                    ...
                ]
            }
        """
        try:
            from api.services.llm_factory import LLMServiceFactory
            from django.conf import settings

            # Check which services are available based on API keys
            available_services = LLMServiceFactory.get_available_services()

            # Model definitions with full details
            # Note: Gemini Flash is NOT included here - it's only used for metadata extraction
            all_models = [
                {
                    "id": "gemini-pro",
                    "name": "Gemini 2.5 Pro",
                    "provider": "Google",
                    "description": "Balanced model for most problems. Good accuracy with moderate cost.",
                    "tier": "moderate",
                    "cost": {
                        "input": 1.25,
                        "output": 5.00,
                        "unit": "per 1M tokens",
                        "estimated_per_problem": "$0.03"
                    },
                    "features": {
                        "reasoning_effort": ["low", "medium"],
                        "max_output_tokens": 8192,
                        "speed": "fast"
                    },
                    "recommended_for": [
                        "Easy to Medium problems (1000-1999 rating)",
                        "Standard competitive programming",
                        "Good balance of cost and quality"
                    ],
                    "available": "gemini" in available_services
                },
                {
                    "id": "gpt-4o",
                    "name": "GPT-4o",
                    "provider": "OpenAI",
                    "description": "Powerful model with strong reasoning. Better than Gemini Pro for complex logic.",
                    "tier": "moderate",
                    "cost": {
                        "input": 2.50,
                        "output": 10.00,
                        "unit": "per 1M tokens",
                        "estimated_per_problem": "$0.06"
                    },
                    "features": {
                        "reasoning_effort": ["low", "medium"],
                        "max_output_tokens": 16384,
                        "speed": "fast"
                    },
                    "recommended_for": [
                        "Medium problems (1500-2499 rating)",
                        "Problems requiring careful logic",
                        "Better code quality than Gemini Pro"
                    ],
                    "available": "openai" in available_services
                },
                {
                    "id": "gpt-5",
                    "name": "GPT-5",
                    "provider": "OpenAI",
                    "description": "Most powerful model with advanced reasoning. Best for hard problems and complex algorithms.",
                    "tier": "complex",
                    "cost": {
                        "input": 10.00,
                        "output": 40.00,
                        "unit": "per 1M tokens",
                        "estimated_per_problem": "$0.20"
                    },
                    "features": {
                        "reasoning_effort": ["low", "medium", "high"],
                        "max_output_tokens": 32768,
                        "extended_thinking": True,
                        "speed": "medium"
                    },
                    "recommended_for": [
                        "Hard problems (2000+ rating)",
                        "Complex algorithms (DP optimization, graph flows)",
                        "Problems requiring deep reasoning",
                        "High reasoning effort available"
                    ],
                    "available": "openai" in available_services,
                    "is_default": True
                }
            ]

            # Filter to only available models
            available_models = [m for m in all_models if m["available"]]

            # Add availability status
            response = {
                "models": available_models,
                "default_model": "gpt-5",
                "default_metadata_extractor": "gemini-flash",
                "metadata": {
                    "total_models": len(all_models),
                    "available_models": len(available_models),
                    "cost_savings_tip": "Use Gemini Flash for metadata extraction (94% cheaper) and GPT-5 only for complex problems"
                }
            }

            # Add configuration hints
            if available_models:
                response["configuration_hints"] = {
                    "easy_problems": {
                        "recommended": "gemini-pro",
                        "reasoning_effort": "low",
                        "max_output_tokens": 8192
                    },
                    "medium_problems": {
                        "recommended": "gpt-4o",
                        "reasoning_effort": "medium",
                        "max_output_tokens": 16384
                    },
                    "hard_problems": {
                        "recommended": "gpt-5",
                        "reasoning_effort": "high",
                        "max_output_tokens": 32768
                    }
                }

            return Response(response, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to get available models: {str(e)}")
            return Response(
                {'error': f'Failed to get available models: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelRecommendationView(APIView):
    """Get model recommendation based on problem difficulty"""
    permission_classes = [AllowAny]

    async def post(self, request):
        """
        Get model recommendation based on problem characteristics

        Request body:
            {
                "difficulty_rating": 2000,  // Optional: Codeforces rating
                "problem_url": "https://...",  // Optional
                "tags": ["dp", "graph"]  // Optional
            }

        Returns:
            {
                "recommended_model": "gpt-5",
                "reasoning_effort": "high",
                "max_output_tokens": 32768,
                "explanation": "This is a hard problem...",
                "alternatives": [...]
            }
        """
        try:
            difficulty_rating = request.data.get('difficulty_rating')
            tags = request.data.get('tags', [])
            problem_url = request.data.get('problem_url', '')

            # Default recommendation
            recommended = {
                "model": "gpt-5",
                "reasoning_effort": "medium",
                "max_output_tokens": 8192
            }

            explanation = []

            # Adjust based on difficulty
            if difficulty_rating:
                if difficulty_rating >= 2500:
                    recommended = {
                        "model": "gpt-5",
                        "reasoning_effort": "high",
                        "max_output_tokens": 32768
                    }
                    explanation.append(f"Difficulty rating {difficulty_rating} (Expert level) - Using GPT-5 with high reasoning")
                elif difficulty_rating >= 2000:
                    recommended = {
                        "model": "gpt-5",
                        "reasoning_effort": "medium",
                        "max_output_tokens": 16384
                    }
                    explanation.append(f"Difficulty rating {difficulty_rating} (Hard) - Using GPT-5 with medium reasoning")
                elif difficulty_rating >= 1500:
                    recommended = {
                        "model": "gpt-4o",
                        "reasoning_effort": "medium",
                        "max_output_tokens": 16384
                    }
                    explanation.append(f"Difficulty rating {difficulty_rating} (Medium) - Using GPT-4o")
                else:
                    recommended = {
                        "model": "gemini-pro",
                        "reasoning_effort": "low",
                        "max_output_tokens": 8192
                    }
                    explanation.append(f"Difficulty rating {difficulty_rating} (Easy) - Using Gemini Pro for cost savings")

            # Adjust based on tags
            complex_tags = ['dp', 'graph', 'tree', 'segment tree', 'flows', 'fft', 'geometry']
            if any(tag.lower() in ' '.join(tags).lower() for tag in complex_tags):
                if recommended["model"] != "gpt-5":
                    recommended["model"] = "gpt-5"
                    recommended["reasoning_effort"] = "high"
                    explanation.append("Complex algorithm detected in tags - Upgraded to GPT-5")

            # Alternative recommendations
            alternatives = []
            if recommended["model"] == "gpt-5":
                alternatives.append({
                    "model": "gpt-4o",
                    "reasoning_effort": "medium",
                    "max_output_tokens": 16384,
                    "cost_savings": "70%",
                    "note": "Cheaper alternative, still good for most problems"
                })
            elif recommended["model"] == "gpt-4o":
                alternatives.append({
                    "model": "gemini-pro",
                    "reasoning_effort": "medium",
                    "max_output_tokens": 8192,
                    "cost_savings": "50%",
                    "note": "More cost-effective, suitable for standard problems"
                })

            return Response({
                "recommended_model": recommended["model"],
                "reasoning_effort": recommended["reasoning_effort"],
                "max_output_tokens": recommended["max_output_tokens"],
                "explanation": " | ".join(explanation) if explanation else "Default recommendation for general problems",
                "alternatives": alternatives,
                "metadata_extraction_note": "Metadata extraction always uses Gemini Flash (most cost-effective)"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to get model recommendation: {str(e)}")
            return Response(
                {'error': f'Failed to get recommendation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
