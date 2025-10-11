"""LLM Service Factory - Choose between Gemini, Gemini Flash, and OpenAI"""
from django.conf import settings
from .gemini_service import GeminiService
from .gemini_flash_service import GeminiFlashService
from .openai_service import OpenAIService
import logging

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory to create appropriate LLM service based on configuration and task tier"""

    # Task tier definitions for cost optimization
    TASK_TIERS = {
        'simple': 'gemini-flash',      # Title, constraints, tags extraction
        'moderate': 'gemini',           # Sample extraction, hints
        'complex': 'openai',            # Hard problem solutions
    }

    @staticmethod
    def create_service(service_type=None, task_tier=None):
        """
        Create LLM service instance based on configuration and task complexity

        Args:
            service_type: Optional override ('gemini', 'gemini-flash', or 'openai')
                         If None, uses DEFAULT_LLM_SERVICE from settings or task_tier
            task_tier: Optional task complexity tier ('simple', 'moderate', 'complex')
                      Used to automatically select cost-effective model

        Returns:
            LLMService instance (GeminiFlashService, GeminiService, or OpenAIService)

        Raises:
            ValueError: If service type is invalid or API key not configured

        Examples:
            # Use tier-based selection (recommended)
            service = LLMServiceFactory.create_service(task_tier='simple')  # Returns GeminiFlashService

            # Direct service selection
            service = LLMServiceFactory.create_service('gemini-flash')  # Returns GeminiFlashService
        """
        # If task_tier provided, use tier-based selection
        if task_tier and service_type is None:
            service_type = LLMServiceFactory.TASK_TIERS.get(task_tier)
            if not service_type:
                raise ValueError(f'Invalid task tier: {task_tier}. Must be "simple", "moderate", or "complex".')
            logger.info(f"Task tier '{task_tier}' mapped to service: {service_type}")

        # Determine which service to use
        if service_type is None:
            service_type = getattr(settings, 'DEFAULT_LLM_SERVICE', 'gemini').lower()

        logger.info(f"Creating LLM service: {service_type}")

        if service_type == 'gemini-flash':
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                raise ValueError('Gemini API key not configured. Set GEMINI_API_KEY in settings.')
            return GeminiFlashService()

        elif service_type == 'gemini':
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                raise ValueError('Gemini API key not configured. Set GEMINI_API_KEY in settings.')
            return GeminiService()

        elif service_type == 'openai':
            if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
                raise ValueError('OpenAI API key not configured. Set OPENAI_API_KEY in settings.')
            return OpenAIService()

        else:
            raise ValueError(f'Invalid LLM service type: {service_type}. Must be "gemini", "gemini-flash", or "openai".')

    @staticmethod
    def get_available_services():
        """
        Get list of available LLM services based on configured API keys

        Returns:
            list: Available service names ['gemini', 'gemini-flash', 'openai']
        """
        available = []

        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            available.append('gemini')
            available.append('gemini-flash')  # Flash uses same API key as Gemini

        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            available.append('openai')

        return available

    @staticmethod
    def get_default_service():
        """
        Get the default LLM service name from settings

        Returns:
            str: Default service name ('gemini' or 'openai')
        """
        return getattr(settings, 'DEFAULT_LLM_SERVICE', 'gemini').lower()


# Convenience function for backwards compatibility
def get_llm_service(service_type=None):
    """
    Get LLM service instance

    Args:
        service_type: Optional service type ('gemini' or 'openai')

    Returns:
        LLMService instance
    """
    return LLMServiceFactory.create_service(service_type)
