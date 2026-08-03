"""
OpenAI provider implementation for LishFind Backend.

Provides integration with OpenAI's GPT models.
"""

import json
from typing import Dict, List, Optional, Any

import structlog
from openai import AsyncOpenAI

from ai.providers.base import AIProvider, AIRequest, AIResponse, AIProviderException
from core.config import settings

logger = structlog.get_logger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, **config):
        """Initialize OpenAI provider."""
        super().__init__(**config)
        
        # Get configuration
        self.api_key = config.get("api_key") or settings.OPENAI_API_KEY
        self.model = config.get("model") or settings.OPENAI_MODEL
        self.max_tokens = config.get("max_tokens") or settings.OPENAI_MAX_TOKENS
        
        if not self.api_key:
            raise AIProviderException(
                "OpenAI API key is required",
                provider="openai",
                error_code="MISSING_API_KEY"
            )
        
        # Initialize client
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        self.logger.info(
            "OpenAI provider initialized",
            model=self.model,
            max_tokens=self.max_tokens
        )
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "openai"
    
    @property
    def supported_models(self) -> List[str]:
        """Return supported OpenAI models."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """Generate text using OpenAI API."""
        
        try:
            # Prepare messages
            messages = []
            
            if request.system_prompt:
                messages.append({
                    "role": "system",
                    "content": request.system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": request.prompt
            })
            
            # Prepare parameters
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": request.max_tokens or self.max_tokens,
                "temperature": request.temperature or 0.7,
            }
            
            self.logger.debug(
                "Making OpenAI API request",
                model=params["model"],
                max_tokens=params["max_tokens"],
                temperature=params["temperature"],
                prompt_length=len(request.prompt)
            )
            
            # Make API call
            response = await self.client.chat.completions.create(**params)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Create response
            ai_response = AIResponse(
                content=content,
                tokens_used=response.usage.total_tokens if response.usage else None,
                model_used=response.model,
                provider=self.provider_name,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                }
            )
            
            self.logger.info(
                "OpenAI API request successful",
                model=ai_response.model_used,
                tokens_used=ai_response.tokens_used,
                response_length=len(content),
                finish_reason=ai_response.metadata.get("finish_reason")
            )
            
            return ai_response
            
        except Exception as e:
            self.logger.error(
                "OpenAI API request failed",
                error=str(e),
                model=self.model,
                exc_info=True
            )
            
            # Determine error type
            error_code = "UNKNOWN_ERROR"
            if "rate_limit" in str(e).lower():
                error_code = "RATE_LIMIT_EXCEEDED"
            elif "invalid" in str(e).lower() and "key" in str(e).lower():
                error_code = "INVALID_API_KEY"
            elif "quota" in str(e).lower():
                error_code = "QUOTA_EXCEEDED"
            
            raise AIProviderException(
                f"OpenAI API error: {str(e)}",
                provider=self.provider_name,
                error_code=error_code
            )
    
    async def generate_structured_response(
        self, 
        request: AIRequest, 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON response using OpenAI API."""
        
        # Enhance prompt with JSON schema instruction
        json_instruction = f"""
        Please respond with valid JSON that matches this schema:
        {json.dumps(schema, indent=2)}
        
        Important:
        - Response must be valid JSON only
        - No additional text outside the JSON
        - Follow the schema exactly
        """
        
        enhanced_request = AIRequest(
            prompt=f"{request.prompt}\n\n{json_instruction}",
            max_tokens=request.max_tokens,
            temperature=request.temperature or 0.3,  # Lower temperature for structured output
            system_prompt=request.system_prompt,
            context=request.context
        )
        
        try:
            # Generate response
            response = await self.generate_text(enhanced_request)
            
            # Parse JSON
            try:
                parsed_json = json.loads(response.content)
                
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
                
                # Try to extract JSON from the response if it's wrapped in text
                content = response.content.strip()
                
                # Look for JSON between ```json and ``` or { and }
                start_markers = ["```json", "```", "{"]
                end_markers = ["```", "}"]
                
                for start_marker in start_markers:
                    if start_marker in content:
                        start_idx = content.find(start_marker)
                        if start_marker == "{":
                            start_idx = content.find("{")
                        else:
                            start_idx = content.find(start_marker) + len(start_marker)
                        
                        for end_marker in end_markers:
                            if end_marker in content[start_idx:]:
                                if end_marker == "}":
                                    end_idx = content.rfind("}") + 1
                                else:
                                    end_idx = start_idx + content[start_idx:].find(end_marker)
                                
                                try:
                                    json_str = content[start_idx:end_idx].strip()
                                    if json_str.startswith("json"):
                                        json_str = json_str[4:].strip()
                                    
                                    parsed_json = json.loads(json_str)
                                    
                                    self.logger.info(
                                        "Successfully extracted JSON from wrapped response",
                                        extracted_json=json_str[:200]
                                    )
                                    
                                    return parsed_json
                                    
                                except json.JSONDecodeError:
                                    continue
                
                raise AIProviderException(
                    f"Invalid JSON response: {str(e)}",
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