"""
Base AI provider interface for LishFind Backend.

Defines the contract that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AIRequest:
    """Standard AI request structure."""
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class AIResponse:
    """Standard AI response structure."""
    content: str
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, **config):
        """Initialize the AI provider with configuration."""
        self.config = config
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported model names."""
        pass
    
    @abstractmethod
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """
        Generate text using the AI model.
        
        Args:
            request: The AI request with prompt and parameters
            
        Returns:
            AIResponse with generated content and metadata
            
        Raises:
            AIProviderException: If the request fails
        """
        pass
    
    @abstractmethod
    async def generate_structured_response(
        self, 
        request: AIRequest, 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured response (JSON) using the AI model.
        
        Args:
            request: The AI request with prompt and parameters
            schema: JSON schema for the expected response structure
            
        Returns:
            Parsed JSON response matching the schema
            
        Raises:
            AIProviderException: If the request fails or response is invalid
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the AI provider.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_request = AIRequest(
                prompt="Hello, this is a test message. Please respond with 'OK'.",
                max_tokens=10
            )
            response = await self.generate_text(test_request)
            
            self.logger.info(
                "AI provider connection test successful",
                provider=self.provider_name,
                response_length=len(response.content)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "AI provider connection test failed",
                provider=self.provider_name,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "name": self.provider_name,
            "supported_models": self.supported_models,
            "config": {k: "***" if "key" in k.lower() else v 
                      for k, v in self.config.items()}
        }


class AIProviderException(Exception):
    """Exception raised by AI providers."""
    
    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(self.message)