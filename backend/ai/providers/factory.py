"""
AI provider factory for LishFind Backend.

Provides a factory to create and manage AI providers based on configuration.
"""

from typing import Dict, Type, Optional

import structlog

from ai.providers.base import AIProvider, AIProviderException
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.gemini_provider import GeminiProvider
from core.config import settings

logger = structlog.get_logger(__name__)


class AIProviderFactory:
    """Factory for creating AI providers."""
    
    # Registry of available providers
    _providers: Dict[str, Type[AIProvider]] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }
    
    # Singleton instance
    _instance: Optional["AIProviderFactory"] = None
    _current_provider: Optional[AIProvider] = None
    
    def __new__(cls) -> "AIProviderFactory":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[AIProvider]) -> None:
        """Register a new AI provider."""
        cls._providers[name] = provider_class
        logger.info("AI provider registered", provider_name=name)
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[AIProvider]]:
        """Get all available AI providers."""
        return cls._providers.copy()
    
    async def create_provider(
        self, 
        provider_name: Optional[str] = None, 
        **config
    ) -> AIProvider:
        """
        Create an AI provider instance.
        
        Args:
            provider_name: Name of the provider to create (defaults to settings.AI_PROVIDER)
            **config: Additional configuration for the provider
            
        Returns:
            AIProvider instance
            
        Raises:
            AIProviderException: If provider is not found or creation fails
        """
        
        # Use configured provider if not specified
        if provider_name is None:
            provider_name = settings.AI_PROVIDER
        
        # Normalize provider name
        provider_name = provider_name.lower().strip()
        
        if provider_name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise AIProviderException(
                f"Unknown AI provider '{provider_name}'. Available providers: {available}",
                provider=provider_name,
                error_code="UNKNOWN_PROVIDER"
            )
        
        try:
            # Get provider class
            provider_class = self._providers[provider_name]
            
            # Create provider instance
            provider = provider_class(**config)
            
            logger.info(
                "AI provider created successfully",
                provider_name=provider_name,
                provider_class=provider_class.__name__
            )
            
            return provider
            
        except Exception as e:
            logger.error(
                "Failed to create AI provider",
                provider_name=provider_name,
                error=str(e),
                exc_info=True
            )
            
            raise AIProviderException(
                f"Failed to create provider '{provider_name}': {str(e)}",
                provider=provider_name,
                error_code="PROVIDER_CREATION_FAILED"
            )
    
    async def get_default_provider(self) -> Optional[AIProvider]:
        """
        Get the default AI provider instance.
        
        Returns:
            Default AIProvider instance (cached) or None if AI is disabled
        """
        
        # Check if AI is disabled
        if settings.AI_PROVIDER == "disabled":
            logger.info("AI provider is disabled - running in free tier mode")
            return None
        
        if self._current_provider is None:
            self._current_provider = await self.create_provider()
            
            # Test the connection
            try:
                connection_ok = await self._current_provider.test_connection()
                if not connection_ok:
                    logger.warning(
                        "Default AI provider connection test failed",
                        provider=self._current_provider.provider_name
                    )
            except Exception as e:
                logger.error(
                    "Error testing default AI provider connection",
                    provider=self._current_provider.provider_name,
                    error=str(e)
                )
        
        return self._current_provider
    
    def reset_provider(self) -> None:
        """Reset the cached provider instance."""
        self._current_provider = None
        logger.info("AI provider cache reset")
    
    async def get_provider_status(self) -> Dict[str, any]:
        """
        Get status of all available providers.
        
        Returns:
            Dictionary with provider status information
        """
        
        status = {
            "default_provider": settings.AI_PROVIDER,
            "available_providers": list(self._providers.keys()),
            "provider_tests": {}
        }
        
        # Test each provider
        for provider_name in self._providers.keys():
            try:
                provider = await self.create_provider(provider_name)
                test_result = await provider.test_connection()
                provider_info = await provider.get_provider_info()
                
                status["provider_tests"][provider_name] = {
                    "available": True,
                    "connection_test": test_result,
                    "info": provider_info
                }
                
            except Exception as e:
                status["provider_tests"][provider_name] = {
                    "available": False,
                    "error": str(e)
                }
        
        return status


# Global factory instance
ai_factory = AIProviderFactory()


async def get_ai_provider(provider_name: Optional[str] = None, **config) -> Optional[AIProvider]:
    """
    Convenience function to get an AI provider instance.
    
    Args:
        provider_name: Name of the provider (defaults to configured provider)
        **config: Additional configuration
        
    Returns:
        AIProvider instance or None if AI is disabled
    """
    if settings.AI_PROVIDER == "disabled":
        return None
        
    if provider_name is None:
        return await ai_factory.get_default_provider()
    else:
        return await ai_factory.create_provider(provider_name, **config)