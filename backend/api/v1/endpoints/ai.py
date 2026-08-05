"""
AI service endpoints for testing and monitoring.

Provides endpoints to test AI functionality and check provider status.
Cloud-optimized for free tier deployment.
"""

from typing import Dict, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth.dependencies import get_optional_current_user
from models.user import User
from services.ai_service import get_ai_service, AIService

logger = structlog.get_logger(__name__)

router = APIRouter()


class AITestRequest(BaseModel):
    """Request schema for AI testing."""
    
    prompt: str = Field(
        ...,
        description="Test prompt for AI",
        example="Hello, this is a test. Please respond with a greeting."
    )
    system_prompt: str = Field(
        None,
        description="Optional system prompt",
        example="You are a helpful assistant for LishFind."
    )
    max_tokens: int = Field(
        100,
        description="Maximum tokens to generate",
        ge=10,
        le=2000
    )
    temperature: float = Field(
        0.7,
        description="Temperature for response creativity",
        ge=0.0,
        le=1.0
    )


class AITestResponse(BaseModel):
    """Response schema for AI testing."""
    
    success: bool = Field(..., description="Whether the test was successful")
    response: str = Field(None, description="AI response content")
    provider: str = Field(None, description="AI provider used")
    tokens_used: int = Field(None, description="Tokens consumed")
    error: str = Field(None, description="Error message if failed")


class AIProviderStatus(BaseModel):
    """Response schema for AI provider status."""
    
    default_provider: str = Field(..., description="Currently configured default provider")
    available_providers: list[str] = Field(..., description="List of available providers")
    provider_tests: Dict[str, Any] = Field(..., description="Status of each provider")


@router.get(
    "/status",
    response_model=AIProviderStatus,
    summary="Get AI provider status",
    description="Get status of all available AI providers and connection tests.",
)
async def get_ai_status(
    ai_service: AIService = Depends(get_ai_service)
) -> AIProviderStatus:
    """Get AI provider status and availability."""
    
    status = await ai_service.get_provider_status()
    
    return AIProviderStatus(
        default_provider=status.get("default_provider", "unknown"),
        available_providers=status.get("available_providers", []),
        provider_tests=status.get("provider_tests", {})
    )


@router.post(
    "/test",
    response_model=AITestResponse,
    summary="Test AI generation",
    description="Test AI text generation with custom prompt. Available for all users in free tier.",
)
async def test_ai_generation(
    test_request: AITestRequest,
    ai_service: AIService = Depends(get_ai_service),
    current_user: User = Depends(get_optional_current_user)
) -> AITestResponse:
    """Test AI text generation."""
    
    try:
        # Generate response using the AI service
        response_text = await ai_service.generate_text(
            prompt=test_request.prompt,
            system_prompt=test_request.system_prompt,
            max_tokens=test_request.max_tokens,
            temperature=test_request.temperature
        )
        
        # Get provider info
        provider_status = await ai_service.test_ai_connection()
        
        logger.info(
            "AI test generation successful",
            user_id=current_user.id if current_user else "anonymous",
            prompt_length=len(test_request.prompt),
            response_length=len(response_text),
            provider=provider_status.get("provider")
        )
        
        return AITestResponse(
            success=True,
            response=response_text,
            provider=provider_status.get("provider"),
            tokens_used=None,  # Would need to track this in AI service
            error=None
        )
        
    except Exception as e:
        logger.error(
            "AI test generation failed",
            user_id=current_user.id if current_user else "anonymous",
            error=str(e),
            exc_info=True
        )
        
        return AITestResponse(
            success=False,
            response=None,
            provider=None,
            tokens_used=None,
            error=str(e)
        )


@router.get(
    "/health",
    summary="AI service health check",
    description="Quick health check for AI service availability.",
)
async def ai_health_check(
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """Quick AI service health check."""
    
    try:
        connection_status = await ai_service.test_ai_connection()
        
        if connection_status.get("available"):
            return {
                "status": "healthy",
                "provider": connection_status.get("provider"),
                "connection_test": connection_status.get("connection_test", False),
                "message": connection_status.get("message", "AI service operational"),
                "features": connection_status.get("features", {})
            }
        else:
            return {
                "status": "unhealthy",
                "error": connection_status.get("error", "Unknown error"),
                "provider": connection_status.get("provider")
            }
            
    except Exception as e:
        logger.error(
            "AI health check failed",
            error=str(e),
            exc_info=True
        )
        
        return {
            "status": "error",
            "error": str(e)
        }