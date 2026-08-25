"""
Azure OpenAI Provider

Implementation of LLMProvider for Azure OpenAI Service.
"""
from typing import List
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

from app.services.llm_service import LLMProvider, LLMMessage, LLMResponse
from app.core.config import settings
from app.core.errors import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """
    Azure OpenAI provider for LLM generation.
    
    Uses Azure OpenAI Service with GPT-4.1-mini deployment.
    
    Configuration (from environment variables):
        - AZURE_OPENAI_API_KEY: Azure OpenAI API key
        - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
        - AZURE_OPENAI_DEPLOYMENT: Deployment name (default: gpt-4.1-mini)
        - AZURE_OPENAI_API_VERSION: API version (default: 2024-12-01-preview)
    
    Security:
        - API key from environment only
        - No credentials in code
        - No credentials in logs
        - Provider errors sanitized before raising
    
    Architecture:
    
        RAGService
            ↓
        LLMService
            ↓
        AzureOpenAIProvider ← THIS
            ↓
        AzureOpenAI client
            ↓
        GPT-4.1-mini
    """
    
    def __init__(self):
        """
        Initialize Azure OpenAI provider.
        
        Raises:
            LLMError: If required configuration is missing
        """
        # Validate configuration
        if not settings.azure_openai_api_key:
            raise LLMError("Azure OpenAI API key not configured")
        
        if not settings.azure_openai_endpoint:
            raise LLMError("Azure OpenAI endpoint not configured")
        
        # Initialize Azure OpenAI client
        try:
            self.client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
            self.deployment = settings.azure_openai_deployment
            
            logger.info(
                "Azure OpenAI provider initialized",
                extra={
                    "deployment": self.deployment,
                    "api_version": settings.azure_openai_api_version
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI provider: {str(e)}")
            raise LLMError("Failed to initialize Azure OpenAI provider")
    
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Generate a completion using Azure OpenAI.
        
        Args:
            messages: List of messages (system, user, assistant)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with generated content
        
        Raises:
            LLMError: If generation fails
        
        Security:
            - Does NOT log full prompt
            - Does NOT log API key
            - Sanitizes provider errors before raising
        """
        try:
            # Convert LLMMessage to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            logger.info(
                "Calling Azure OpenAI",
                extra={
                    "deployment": self.deployment,
                    "message_count": len(openai_messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            # Call Azure OpenAI
            completion: ChatCompletion = self.client.chat.completions.create(
                model=self.deployment,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                n=1  # Single completion
            )
            
            # Extract response
            choice = completion.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or "stop"
            
            # Extract token usage
            usage = completion.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            logger.info(
                "Azure OpenAI response received",
                extra={
                    "finish_reason": finish_reason,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            )
            
            return LLMResponse(
                content=content,
                model=self.deployment,
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            # Sanitize error - do NOT expose provider details
            logger.error(
                "Azure OpenAI generation failed",
                extra={"error_type": type(e).__name__}
            )
            raise LLMError(
                message="Failed to generate LLM response",
                details={"error_type": type(e).__name__}
            )


def get_azure_openai_provider() -> AzureOpenAIProvider:
    """
    Factory function to get Azure OpenAI provider.
    
    Returns:
        AzureOpenAIProvider instance
    
    Raises:
        LLMError: If provider initialization fails
    """
    return AzureOpenAIProvider()
