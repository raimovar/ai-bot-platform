"""
Base AI Provider
Abstract interface for LLM providers
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Supported provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    HUGGINGFACE = "huggingface"
    MISTRAL = "mistral"
    GROQ = "groq"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers

    All LLM providers should implement this interface.

    Usage:
        provider = get_provider("openai", model_name="gpt-4", api_key="...")

        response = await provider.generate(
            messages=[{"role": "user", "content": "Hello!"}],
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=1000,
        )

        print(response.content)
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.config = config or {}

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return provider type"""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Get model context window size"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> AIResponse:
        """
        Generate a response

        Args:
            messages: List of message dicts with role and content
            system_prompt: System prompt to prepend
            temperature: Sampling temperature (0-2)
            max_tokens: Max tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences

        Returns:
            AIResponse with generated content
        """
        pass

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ):
        """
        Generate a streaming response

        Yields chunks of content as they arrive.

        Args:
            Same as generate()

        Yields:
            Content chunks as strings
        """
        if not self.supports_streaming:
            raise NotImplementedError(f"{self.provider_type} does not support streaming")

        # Default implementation: accumulate and yield
        response = await self.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield response.content

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        pass

    async def validate_config(self) -> bool:
        """
        Validate provider configuration

        Returns:
            True if configuration is valid
        """
        if not self.api_key and not self.base_url:
            return False
        return True

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "provider": self.provider_type.value,
            "model": self.model_name,
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
        }
