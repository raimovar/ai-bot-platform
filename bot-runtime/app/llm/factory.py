"""
LLM Factory - Unified interface for multiple LLM providers.
"""
from typing import Optional
import httpx


class BaseLLM:
    """Base class for LLM providers."""
    
    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
    
    async def generate(self, messages: list[dict], **kwargs) -> dict:
        """Generate a response."""
        raise NotImplementedError


class OpenAIProvider(BaseLLM):
    """OpenAI API provider."""
    
    async def generate(self, messages: list[dict], **kwargs) -> dict:
        """Call OpenAI API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "top_p": kwargs.get("top_p"),
            "frequency_penalty": kwargs.get("frequency_penalty"),
            "presence_penalty": kwargs.get("presence_penalty"),
        }
        
        # Add tools if provided
        if kwargs.get("tools"):
            payload["tools"] = kwargs["tools"]
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        base = self.base_url or "https://api.openai.com/v1"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()


class AnthropicProvider(BaseLLM):
    """Anthropic API provider."""
    
    async def generate(self, messages: list[dict], **kwargs) -> dict:
        """Call Anthropic API."""
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        # Convert messages format
        system = ""
        formatted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                role = "assistant" if msg["role"] == "assistant" else "user"
                formatted_messages.append({
                    "role": role,
                    "content": msg["content"],
                })
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        
        if system:
            payload["system"] = system
        
        base = self.base_url or "https://api.anthropic.com/v1"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            
            # Convert to OpenAI format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": result["content"][0]["text"],
                    }
                }],
                "model": self.model,
                "usage": {
                    "input_tokens": result["usage"]["input_tokens"],
                    "output_tokens": result["usage"]["output_tokens"],
                    "total_tokens": result["usage"]["input_tokens"] + result["usage"]["output_tokens"],
                },
            }


class OllamaProvider(BaseLLM):
    """Ollama local LLM provider."""
    
    async def generate(self, messages: list[dict], **kwargs) -> dict:
        """Call Ollama API."""
        # Convert messages format
        formatted_messages = []
        for msg in messages:
            if msg["role"] != "system":
                formatted_messages.append(msg)
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        
        base = self.base_url or "http://localhost:11434"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{base}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            
            # Convert to OpenAI format
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": result["message"]["content"],
                    }
                }],
                "model": self.model,
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                },
            }


class LLMFactory:
    """Factory for creating LLM provider instances."""
    
    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "lmstudio": OpenAIProvider,  # Compatible with OpenAI format
        "huggingface": OpenAIProvider,  # May need adjustment
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseLLM:
        """
        Create an LLM provider instance.
        
        Args:
            provider: Provider name (openai, anthropic, ollama, etc.)
            model: Model name
            api_key: API key (optional for local providers)
            base_url: Custom base URL (for proxies or local)
        
        Returns:
            LLM provider instance
        """
        provider_class = cls._providers.get(provider.lower())
        
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider}")
        
        return provider_class(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a new provider."""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List available providers."""
        return list(cls._providers.keys())
