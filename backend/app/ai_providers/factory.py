"""
AI Provider Factory
Creates AI provider instances
"""

from typing import Optional, Dict, Any, Type

from .base import BaseAIProvider, ProviderType
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider


# Provider registry
_PROVIDERS: Dict[ProviderType, Type[BaseAIProvider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.OLLAMA: OllamaProvider,
}

# Aliases for provider names
_PROVIDER_ALIASES: Dict[str, ProviderType] = {
    # OpenAI
    "openai": ProviderType.OPENAI,
    "gpt": ProviderType.OPENAI,
    "gpt-4": ProviderType.OPENAI,
    "gpt-3.5": ProviderType.OPENAI,
    # Anthropic
    "anthropic": ProviderType.ANTHROPIC,
    "claude": ProviderType.ANTHROPIC,
    "claude-3": ProviderType.ANTHROPIC,
    "claude-3.5": ProviderType.ANTHROPIC,
    # Ollama
    "ollama": ProviderType.OLLAMA,
    "local": ProviderType.OLLAMA,
    "llama": ProviderType.OLLAMA,
    "llama3": ProviderType.OLLAMA,
    "mistral": ProviderType.OLLAMA,
    "mixtral": ProviderType.OLLAMA,
    "codellama": ProviderType.OLLAMA,
}


def get_provider_type(name: str) -> ProviderType:
    """
    Get provider type from name

    Args:
        name: Provider name (openai, anthropic, ollama, etc.)

    Returns:
        ProviderType enum value
    """
    name_lower = name.lower()

    # Check aliases
    if name_lower in _PROVIDER_ALIASES:
        return _PROVIDER_ALIASES[name_lower]

    # Try as ProviderType value
    try:
        return ProviderType(name_lower)
    except ValueError:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_PROVIDER_ALIASES.keys())}")


def get_provider(
    provider_type: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> BaseAIProvider:
    """
    Create an AI provider instance

    Args:
        provider_type: Provider type (openai, anthropic, ollama, etc.)
        model_name: Model name to use
        api_key: API key (for cloud providers)
        base_url: Base URL (for self-hosted)
        config: Additional configuration

    Returns:
        Configured AI provider instance

    Example:
        # OpenAI
        provider = get_provider("openai", model_name="gpt-4", api_key="sk-...")

        # Anthropic
        provider = get_provider("anthropic", model_name="claude-3-sonnet", api_key="sk-ant-...")

        # Ollama (local)
        provider = get_provider("ollama", model_name="llama3.2", base_url="http://localhost:11434")
    """
    provider = get_provider_type(provider_type)
    provider_class = _PROVIDERS.get(provider)

    if not provider_class:
        raise ValueError(f"No provider implementation for {provider}")

    # Set defaults based on provider
    defaults = _get_provider_defaults(provider)
    model_name = model_name or defaults.get("model_name")
    base_url = base_url or defaults.get("base_url")

    return provider_class(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        config=config or {},
    )


def _get_provider_defaults(provider: ProviderType) -> Dict[str, str]:
    """Get default values for a provider"""
    defaults = {
        ProviderType.OPENAI: {
            "model_name": "gpt-3.5-turbo",
            "base_url": "https://api.openai.com/v1",
        },
        ProviderType.ANTHROPIC: {
            "model_name": "claude-3-5-sonnet-20241022",
            "base_url": "https://api.anthropic.com/v1",
        },
        ProviderType.OLLAMA: {
            "model_name": "llama3.2",
            "base_url": "http://localhost:11434",
        },
    }
    return defaults.get(provider, {})


def list_providers() -> Dict[str, Dict[str, Any]]:
    """
    List all available providers and their info

    Returns:
        Dict of provider info
    """
    return {
        "openai": {
            "name": "OpenAI",
            "description": "OpenAI GPT-4, GPT-3.5 Turbo models",
            "requires_api_key": True,
            "default_model": "gpt-3.5-turbo",
            "supports_streaming": True,
        },
        "anthropic": {
            "name": "Anthropic",
            "description": "Claude 3 models",
            "requires_api_key": True,
            "default_model": "claude-3-5-sonnet-20241022",
            "supports_streaming": True,
        },
        "ollama": {
            "name": "Ollama",
            "description": "Local LLM inference with Ollama",
            "requires_api_key": False,
            "default_model": "llama3.2",
            "supports_streaming": True,
        },
    }


def register_provider(provider_type: ProviderType, provider_class: Type[BaseAIProvider]):
    """
    Register a custom provider

    Args:
        provider_type: Provider type enum
        provider_class: Provider class implementation
    """
    _PROVIDERS[provider_type] = provider_class
    _PROVIDER_ALIASES[provider_type.value] = provider_type


__all__ = [
    "get_provider",
    "get_provider_type",
    "list_providers",
    "register_provider",
    "BaseAIProvider",
    "ProviderType",
]
