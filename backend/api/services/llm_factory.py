"""LLM Service Factory - Choose between Gemini and OpenAI"""
from django.conf import settings
from .gemini_service import GeminiService
from .openai_service import OpenAIService
import logging

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory to create appropriate LLM service based on configuration"""

    @staticmethod
    def create_service(service_type=None):
        """
        Create LLM service instance based on configuration

        Args:
            service_type: Optional override ('gemini' or 'openai')
                         If None, uses DEFAULT_LLM_SERVICE from settings

        Returns:
            LLMService instance (GeminiService or OpenAIService)

        Raises:
            ValueError: If service type is invalid or API key not configured
        """
        # Determine which service to use
        if service_type is None:
            service_type = getattr(settings, 'DEFAULT_LLM_SERVICE', 'gemini').lower()

        logger.info(f"Creating LLM service: {service_type}")

        if service_type == 'gemini':
            if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
                raise ValueError('Gemini API key not configured. Set GEMINI_API_KEY in settings.')
            return GeminiService()

        elif service_type == 'openai':
            if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
                raise ValueError('OpenAI API key not configured. Set OPENAI_API_KEY in settings.')
            return OpenAIService()

        else:
            raise ValueError(f'Invalid LLM service type: {service_type}. Must be "gemini" or "openai".')

    @staticmethod
    def get_available_services():
        """
        Get list of available LLM services based on configured API keys

        Returns:
            list: Available service names ['gemini', 'openai']
        """
        available = []

        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            available.append('gemini')

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
