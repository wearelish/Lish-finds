"""
AI service for LishFind Backend.

Provides high-level AI functionality using the configured AI provider.
For free tier, provides mock responses when AI is disabled.
"""

from typing import Dict, List, Optional, Any

import structlog

from ai.providers.base import AIProvider, AIRequest, AIResponse, AIProviderException
from ai.providers.factory import ai_factory
from core.config import settings
from core.exceptions import ExternalServiceException

logger = structlog.get_logger(__name__)


class AIService:
    """High-level AI service for LishFind operations."""
    
    def __init__(self):
        self._provider: Optional[AIProvider] = None
    
    async def _get_provider(self) -> Optional[AIProvider]:
        """Get the AI provider instance. Returns None if AI is disabled."""
        if settings.AI_PROVIDER == "disabled":
            return None
            
        if self._provider is None:
            try:
                self._provider = await ai_factory.get_default_provider()
            except AIProviderException as e:
                logger.warning(
                    "AI provider unavailable, using mock responses",
                    provider=settings.AI_PROVIDER,
                    error=str(e)
                )
                return None
        
        return self._provider
    
    def _mock_ai_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate mock AI responses for free tier."""
        prompt_lower = prompt.lower()
        
        # Mock business recommendations
        if "recommend" in prompt_lower or "suggestion" in prompt_lower:
            return "Based on your preferences, here are some popular local businesses in your area."
        
        # Mock search intent
        if "search" in prompt_lower or "find" in prompt_lower:
            return "I understand you're looking for local businesses. Let me help you with that search."
        
        # Mock business description
        if "describe" in prompt_lower or "about" in prompt_lower:
            return "This is a well-established local business serving the community with quality services."
        
        # Default mock response
        return "Thank you for your query. This is a demo response as AI features require paid API keys."
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate text using AI or mock response for free tier.
        
        Args:
            prompt: The input prompt
            system_prompt: System instructions (optional)
            max_tokens: Maximum tokens to generate (optional)
            temperature: Response creativity (optional)
            context: Additional context (optional)
            
        Returns:
            Generated text response
        """
        
        provider = await self._get_provider()
        
        if provider is None:
            # Return mock response for free tier
            logger.info("Using mock AI response (AI provider disabled)")
            return self._mock_ai_response(prompt, context)
        
        try:
            # Use real AI provider if available
            request = AIRequest(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens or 150,
                temperature=temperature or 0.7,
                context=context or {}
            )
            
            response = await provider.generate(request)
            
            logger.info(
                "AI text generation successful",
                provider=provider.provider_name,
                prompt_length=len(prompt),
                response_length=len(response.content)
            )
            
            return response.content
            
        except Exception as e:
            logger.warning(
                "AI generation failed, using mock response",
                error=str(e),
                provider=provider.provider_name if provider else "unknown"
            )
            return self._mock_ai_response(prompt, context)
    
    async def test_ai_connection(self) -> Dict[str, Any]:
        """
        Test AI provider connection and return status.
        
        Returns:
            Dictionary with connection status and provider info
        """
        
        provider = await self._get_provider()
        
        if provider is None:
            return {
                "available": False,
                "provider": "disabled",
                "message": "AI provider is disabled for free tier operation"
            }
        
        try:
            # Test connection
            connection_ok = await provider.test_connection()
            provider_info = await provider.get_provider_info()
            
            return {
                "available": True,
                "provider": provider_info["name"],
                "connection_test": connection_ok,
                "supported_models": provider_info.get("supported_models", [])
            }
            
        except Exception as e:
            logger.error(
                "AI connection test failed",
                error=str(e),
                exc_info=True
            )
            
            return {
                "available": False,
                "error": str(e),
                "provider": settings.AI_PROVIDER
            }
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """
        Get comprehensive AI provider status.
        
        Returns:
            Dictionary with all available providers and their status
        """
        
        if settings.AI_PROVIDER == "disabled":
            return {
                "default_provider": "disabled",
                "available_providers": [],
                "message": "AI features disabled for free tier operation",
                "free_tier": True
            }
        
        try:
            return await ai_factory.get_provider_status()
            
        except Exception as e:
            logger.error(
                "Failed to get provider status",
                error=str(e),
                exc_info=True
            )
            
            return {
                "error": str(e),
                "default_provider": settings.AI_PROVIDER,
                "available_providers": []
            }