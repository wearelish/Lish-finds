"""
Google Gemini provider implementation for LishFind Backend.

Provides integration with Google's Gemini models.
"""

import json
from typing import Dict, List, Optional, Any

import structlog
import google.generativeai as genai

from ai.providers.base import AIProvider, AIRequest, AIResponse, AIProviderException
from core.config import settings

logger = structlog.get_logger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, **config):
        """Initialize Gemini provider."""
        super().__init__(**config)
        
        # Get configuration
        self.api_key = config.get("api_key") or settings.GEMINI_API_KEY
        self.model_name = config.get("model") or settings.GEMINI_MODEL
        
        if not self.api_key:
            raise AIProviderException(
                "Gemini API key is required",
                provider="gemini",
                error_code="MISSING_API_KEY"
            )
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        try:
            self.model = genai.GenerativeModel(self.model_name)
            self.logger.info(
                "Gemini provider initialized",
                model=self.model_name
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize Gemini model",
                model=self.model_name,
                error=str(e)
            )
            raise AIProviderException(
                f"Failed to initialize Gemini model: {str(e)}",
                provider="gemini",
                error_code="MODEL_INITIALIZATION_FAILED"
            )
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gemini"
    
    @property
    def supported_models(self) -> List[str]:
        """Return supported Gemini models."""
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
    
    def _prepare_generation_config(self, request: AIRequest) -> Dict[str, Any]:
        """Prepare generation configuration for Gemini."""
        config = {}
        
        if request.max_tokens:
            config["max_output_tokens"] = request.max_tokens
        
        if request.temperature is not None:
            config["temperature"] = request.temperature
        
        return config
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """Generate text using Gemini API."""
        
        try:
            # Prepare the prompt
            full_prompt = request.prompt
            
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"
            
            # Prepare generation config
            generation_config = self._prepare_generation_config(request)
            
            self.logger.debug(
                "Making Gemini API request",
                model=self.model_name,
                generation_config=generation_config,
                prompt_length=len(full_prompt)
            )
            
            # Generate content
            if generation_config:
                response = await self.model.generate_content_async(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(**generation_config)
                )
            else:
                response = await self.model.generate_content_async(full_prompt)
            
            # Extract content
            content = response.text
            
            # Create response
            ai_response = AIResponse(
                content=content,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                model_used=self.model_name,
                provider=self.provider_name,
                metadata={
                    "finish_reason": getattr(response.candidates[0], 'finish_reason', None) if response.candidates else None,
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None,
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in (response.candidates[0].safety_ratings if response.candidates else [])
                    ]
                }
            )
            
            self.logger.info(
                "Gemini API request successful",
                model=ai_response.model_used,
                tokens_used=ai_response.tokens_used,
                response_length=len(content),
                finish_reason=ai_response.metadata.get("finish_reason")
            )
            
            return ai_response
            
        except Exception as e:
            self.logger.error(
                "Gemini API request failed",
                error=str(e),
                model=self.model_name,
                exc_info=True
            )
            
            # Determine error type
            error_code = "UNKNOWN_ERROR"
            error_str = str(e).lower()
            
            if "quota" in error_str or "limit" in error_str:
                error_code = "QUOTA_EXCEEDED"
            elif "key" in error_str and ("invalid" in error_str or "unauthorized" in error_str):
                error_code = "INVALID_API_KEY"
            elif "safety" in error_str or "blocked" in error_str:
                error_code = "CONTENT_BLOCKED"
            elif "model" in error_str and "not found" in error_str:
                error_code = "MODEL_NOT_FOUND"
            
            raise AIProviderException(
                f"Gemini API error: {str(e)}",
                provider=self.provider_name,
                error_code=error_code
            )
    
    async def generate_structured_response(
        self, 
        request: AIRequest, 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON response using Gemini API."""
        
        # Enhance prompt with JSON schema instruction
        json_instruction = f"""
        Please respond with valid JSON that matches this exact schema:
        {json.dumps(schema, indent=2)}
        
        Requirements:
        - Output must be valid JSON only
        - No additional text, explanations, or formatting
        - Follow the schema structure exactly
        - Use appropriate data types as specified
        """
        
        enhanced_request = AIRequest(
            prompt=f"{request.prompt}\n\n{json_instruction}",
            max_tokens=request.max_tokens,
            temperature=request.temperature or 0.2,  # Lower temperature for structured output
            system_prompt=request.system_prompt,
            context=request.context
        )
        
        try:
            # Generate response
            response = await self.generate_text(enhanced_request)
            
            # Parse JSON
            try:
                # Clean up the response content
                content = response.content.strip()
                
                # Remove markdown formatting if present
                if content.startswith("```json"):
                    content = content[7:]  # Remove ```json
                if content.startswith("```"):
                    content = content[3:]   # Remove ```
                if content.endswith("```"):
                    content = content[:-3]  # Remove ending ```
                
                content = content.strip()
                
                parsed_json = json.loads(content)
                
                self.logger.debug(
                    "Structured response generated successfully",
                    schema_keys=list(schema.keys()) if isinstance(schema, dict) else None,
                    response_keys=list(parsed_json.keys()) if isinstance(parsed_json, dict) else None
                )
                
                return parsed_json
                
            except json.JSONDecodeError as e:
                self.logger.error(
                    "Failed to parse JSON response",
                    response_content=response.content[:500],  # First 500 chars for debugging
                    json_error=str(e)
                )
                
                # Try to extract JSON from the response
                content = response.content
                
                # Find the first { and last } to extract potential JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    try:
                        json_str = content[start_idx:end_idx + 1]
                        parsed_json = json.loads(json_str)
                        
                        self.logger.info(
                            "Successfully extracted JSON from Gemini response",
                            extracted_json=json_str[:200]
                        )
                        
                        return parsed_json
                        
                    except json.JSONDecodeError:
                        pass
                
                raise AIProviderException(
                    f"Invalid JSON response from Gemini: {str(e)}",
                    provider=self.provider_name,
                    error_code="INVALID_JSON_RESPONSE"
                )
                
        except AIProviderException:
            raise
        except Exception as e:
            self.logger.error(
                "Structured response generation failed",
                error=str(e),
                exc_info=True
            )
            raise AIProviderException(
                f"Failed to generate structured response: {str(e)}",
                provider=self.provider_name,
                error_code="STRUCTURED_GENERATION_FAILED"
            )