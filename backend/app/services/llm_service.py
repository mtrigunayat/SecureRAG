"""
LLM Service

Abstract interface for Large Language Model providers.
Decouples business logic from specific LLM implementations.
"""
from typing import Protocol, List, Dict, Any
from abc import abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """
    LLM message structure.
    
    Represents a single message in a conversation.
    """
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """
    Normalized LLM response.
    
    Provider-agnostic response format to avoid leaking
    provider-specific objects throughout the application.
    """
    content: str
    model: str
    finish_reason: str = "stop"
    
    # Optional metadata
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMProvider(Protocol):
    """
    Protocol for LLM providers.
    
    Implementations:
        - AzureOpenAIProvider (GPT-4.1-mini via Azure)
        - OpenAIProvider (future)
        - AnthropicProvider (future)
        - LocalLLMProvider (future)
    
    All providers must implement the `generate` method.
    """
    
    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of messages (system, user, assistant)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with generated content and metadata
        
        Raises:
            LLMError: If generation fails
        """
        pass


class LLMService:
    """
    LLM service abstraction.
    
    Provides a clean interface for generating text with LLMs.
    Business logic depends on this service, NOT on provider-specific clients.
    
    Architecture:
    
        RAGService
            ↓
        LLMService
            ↓
        LLMProvider (Azure, OpenAI, etc.)
            ↓
        Actual LLM (GPT-4.1-mini, Claude, etc.)
    
    Security:
        - Provider credentials are environment-based
        - No credentials in code
        - No credentials in logs
        - No credentials in responses
    """
    
    def __init__(self, provider: LLMProvider):
        """
        Initialize LLM service with a provider.
        
        Args:
            provider: LLM provider implementation
        """
        self.provider = provider
    
    def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Delegates to the configured provider.
        
        Args:
            messages: List of messages (system, user, assistant)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with generated content
        
        Raises:
            LLMError: If generation fails
        """
        return self.provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
