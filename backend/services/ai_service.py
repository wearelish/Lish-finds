"""
AI Service for LishFind Backend

Cloud-optimized AI service that provides mock responses for free tier
and real AI functionality for premium deployments.
"""

import json
import random
import time
from typing import Dict, List, Optional, Any

import structlog
from pydantic import BaseModel

from core.config import settings

logger = structlog.get_logger(__name__)


class AIResponse(BaseModel):
    """Standard AI response format."""
    response: str
    provider: str
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None
    confidence: Optional[float] = None


class AIService:
    """
    AI service with cloud deployment optimization.
    
    Provides mock responses when AI_PROVIDER is 'disabled' for free tier,
    and real AI integration when providers are configured.
    """
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.mock_responses = self._load_mock_responses()
    
    def _load_mock_responses(self) -> Dict[str, List[str]]:
        """Load mock responses for free tier."""
        return {
            "greeting": [
                "Hello! LishFind is working perfectly. This is a mock AI response for the free tier.",
                "Hi there! Your backend is connected and ready. This demonstrates the AI integration.",
                "Welcome to LishFind! The API is functioning correctly with mock AI responses."
            ],
            "search_intent": [
                "I understand you're looking for a place to visit. Let me help you find what you need.",
                "Based on your query, I can help you discover local businesses that match your preferences.",
                "Your search intent has been processed. Here are some suggestions based on your request."
            ],
            "business_summary": [
                "This is a popular local business with great reviews and good service.",
                "Customers frequently praise this place for its quality and atmosphere.",
                "This establishment is known for excellent customer service and value."
            ],
            "recommendation": [
                "Based on your preferences, I recommend checking out this highly-rated option.",
                "This place seems perfect for what you're looking for - great reviews and good location.",
                "You might enjoy this spot - it matches your criteria and has excellent feedback."
            ]
        }
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7,
        category: str = "greeting"
    ) -> str:
        """
        Generate text response.
        
        Uses mock responses for free tier (AI_PROVIDER=disabled)
        or real AI for configured providers.
        """
        start_time = time.time()
        
        try:
            if self.provider == "disabled":
                # Mock response for free tier
                response = self._generate_mock_response(prompt, category)
                
                # Simulate processing time
                processing_time = random.uniform(0.5, 1.5)
                await self._simulate_delay(processing_time)
                
                logger.info(
                    "Mock AI response generated",
                    provider="mock",
                    prompt_length=len(prompt),
                    response_length=len(response),
                    processing_time_ms=int(processing_time * 1000)
                )
                
                return response
            
            elif self.provider == "openai":
                return await self._generate_openai_response(prompt, system_prompt, max_tokens, temperature)
            
            elif self.provider == "gemini":
                return await self._generate_gemini_response(prompt, system_prompt, max_tokens, temperature)
            
            else:
                raise ValueError(f"Unknown AI provider: {self.provider}")
                
        except Exception as e:
            logger.error(
                "AI text generation failed",
                provider=self.provider,
                error=str(e),
                prompt_length=len(prompt)
            )
            
            # Fallback to mock response
            return self._generate_mock_response(prompt, "error")
    
    def _generate_mock_response(self, prompt: str, category: str = "greeting") -> str:
        """Generate mock AI response for free tier."""
        
        # Select appropriate response category based on prompt content
        if any(word in prompt.lower() for word in ["hello", "hi", "test", "greeting"]):
            category = "greeting"
        elif any(word in prompt.lower() for word in ["search", "find", "looking", "want"]):
            category = "search_intent"
        elif any(word in prompt.lower() for word in ["business", "place", "restaurant", "shop"]):
            category = "business_summary"
        elif any(word in prompt.lower() for word in ["recommend", "suggest", "best"]):
            category = "recommendation"
        
        responses = self.mock_responses.get(category, self.mock_responses["greeting"])
        response = random.choice(responses)
        
        # Add context about being a mock response
        return f"{response}\n\n*This is a mock response for demonstration. Enable AI providers in production for real AI functionality.*"
    
    async def _simulate_delay(self, seconds: float):
        """Simulate AI processing delay."""
        import asyncio
        await asyncio.sleep(seconds)
    
    async def _generate_openai_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> str:
        """Generate response using OpenAI API."""
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        try:
            # Import OpenAI client
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("OpenAI API request failed", error=str(e))
            raise
    
    async def _generate_gemini_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> str:
        """Generate response using Google Gemini API."""
        
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        try:
            # Import Google AI client
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            
            response = await model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error("Gemini API request failed", error=str(e))
            raise
    
    async def test_ai_connection(self) -> Dict[str, Any]:
        """Test AI connection and provider availability."""
        
        if self.provider == "disabled":
            return {
                "available": True,
                "provider": "mock",
                "connection_test": True,
                "message": "Mock AI provider active (free tier)",
                "features": {
                    "text_generation": True,
                    "intent_extraction": True,
                    "recommendations": True,
                    "real_time": False
                }
            }
        
        try:
            # Test with a simple prompt
            test_response = await self.generate_text(
                "Hello, this is a connection test.",
                max_tokens=20,
                temperature=0.1
            )
            
            return {
                "available": True,
                "provider": self.provider,
                "connection_test": True,
                "test_response": test_response[:100],
                "features": {
                    "text_generation": True,
                    "intent_extraction": True,
                    "recommendations": True,
                    "real_time": True
                }
            }
            
        except Exception as e:
            logger.error("AI connection test failed", provider=self.provider, error=str(e))
            
            return {
                "available": False,
                "provider": self.provider,
                "connection_test": False,
                "error": str(e),
                "features": {
                    "text_generation": False,
                    "intent_extraction": False,
                    "recommendations": False,
                    "real_time": False
                }
            }
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get comprehensive provider status."""
        
        available_providers = ["disabled"]  # Always available
        
        # Check OpenAI availability
        if settings.OPENAI_API_KEY:
            available_providers.append("openai")
        
        # Check Gemini availability  
        if settings.GEMINI_API_KEY:
            available_providers.append("gemini")
        
        provider_tests = {}
        
        # Test current provider
        current_test = await self.test_ai_connection()
        provider_tests[self.provider] = current_test
        
        return {
            "default_provider": self.provider,
            "available_providers": available_providers,
            "provider_tests": provider_tests,
            "recommendations": self._get_provider_recommendations()
        }
    
    def _get_provider_recommendations(self) -> Dict[str, str]:
        """Get recommendations for AI provider setup."""
        
        recommendations = {}
        
        if self.provider == "disabled":
            recommendations["current"] = "Running in free tier mode with mock responses"
            
            if not settings.OPENAI_API_KEY and not settings.GEMINI_API_KEY:
                recommendations["upgrade"] = "Add OPENAI_API_KEY or GEMINI_API_KEY to enable real AI features"
        
        return recommendations
    
    # Intent extraction helpers
    async def extract_intent_mock(self, query: str) -> Dict[str, Any]:
        """Mock intent extraction for free tier."""
        
        # Simple keyword-based intent detection
        query_lower = query.lower()
        
        # Detect category
        category = "general"
        if any(word in query_lower for word in ["restaurant", "food", "eat", "dinner", "lunch"]):
            category = "restaurant"
        elif any(word in query_lower for word in ["coffee", "café", "cafe"]):
            category = "cafe"
        elif any(word in query_lower for word in ["shop", "store", "buy", "shopping"]):
            category = "shopping"
        elif any(word in query_lower for word in ["hotel", "stay", "accommodation"]):
            category = "accommodation"
        
        # Detect budget indicators
        budget_range = "moderate"
        if any(word in query_lower for word in ["cheap", "budget", "affordable", "under"]):
            budget_range = "budget"
        elif any(word in query_lower for word in ["expensive", "premium", "luxury"]):
            budget_range = "premium"
        
        # Detect mood/atmosphere
        atmosphere = []
        if any(word in query_lower for word in ["quiet", "peaceful", "calm"]):
            atmosphere.append("quiet")
        if any(word in query_lower for word in ["busy", "lively", "energetic"]):
            atmosphere.append("lively")
        if any(word in query_lower for word in ["romantic", "date", "intimate"]):
            atmosphere.append("romantic")
        
        # Mock confidence based on query complexity
        confidence = 0.75 + (len(query.split()) * 0.02)
        confidence = min(confidence, 0.95)
        
        return {
            "success": True,
            "category": category,
            "budget_range": budget_range,
            "atmosphere": atmosphere,
            "keywords": query.split(),
            "confidence": confidence,
            "provider": "mock",
            "processing_time_ms": random.randint(100, 300)
        }


# Global AI service instance
ai_service = AIService()


async def get_ai_service() -> AIService:
    """Dependency to get AI service instance."""
    return ai_service