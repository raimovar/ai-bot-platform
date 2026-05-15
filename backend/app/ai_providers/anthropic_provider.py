"""
Anthropic Provider
Anthropic Claude API integration
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

from .base import BaseAIProvider, AIResponse, ProviderType

logger = logging.getLogger(__name__)

# Anthropic model info
MODEL_INFO = {
    "claude-3-5-sonnet": {"context": 200000, "supports_vision": True},
    "claude-3-5-haiku": {"context": 200000, "supports_vision": True},
    "claude-3-opus": {"context": 200000, "supports_vision": True},
    "claude-3-sonnet": {"context": 200000, "supports_vision": True},
    "claude-3-haiku": {"context": 200000, "supports_vision": True},
    "claude-2.1": {"context": 200000, "supports_vision": False},
    "claude-2": {"context": 100000, "supports_vision": False},
}


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude API provider

    Supports Claude 3 models.
    """

    BASE_URL = "https://api.anthropic.com/v1"
    COMPLETIONS_URL = "/messages"

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name, api_key, base_url, config)
        self._base_url = base_url or self.BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def context_window(self) -> int:
        """Get context window based on model"""
        for prefix, info in MODEL_INFO.items():
            if self.model_name.startswith(prefix):
                return info["context"]
        return 200000  # Default to Claude 3 context

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

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
        """Generate response from Anthropic"""
        if not self.api_key:
            return AIResponse(
                content="",
                model=self.model_name,
                provider=self.provider_type.value,
                error="API key not configured",
            )

        # Build messages - Anthropic format
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "user", "content": system_prompt})
        all_messages.extend(messages)

        # Convert to Anthropic format
        anthropic_messages = []
        for msg in all_messages:
            role = msg["role"]
            if role == "system":
                # Add as user message for simplicity
                continue
            if role == "assistant":
                role = "assistant"
            else:
                role = "user"
            anthropic_messages.append({"role": role, "content": msg["content"]})

        # Build request
        data = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_prompt:
            data["system"] = system_prompt

        if top_p:
            data["top_p"] = top_p
        if stop:
            data["stop_sequences"] = stop

        data.update(kwargs)

        try:
            client = self._get_client()
            start_time = asyncio.get_event_loop().time()

            response = await client.post(
                f"{self._base_url}{self.COMPLETIONS_URL}",
                json=data,
            )

            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            if response.status_code != 200:
                error_data = response.json()
                return AIResponse(
                    content="",
                    model=self.model_name,
                    provider=self.provider_type.value,
                    error=f"API error {response.status_code}: {error_data.get('error', {}).get('message', 'Unknown')}",
                )

            result = response.json()

            return AIResponse(
                content=result["content"][0]["text"],
                model=result.get("model", self.model_name),
                provider=self.provider_type.value,
                tokens_used=result.get("usage", {}).get("total_tokens"),
                prompt_tokens=result.get("usage", {}).get("input_tokens"),
                completion_tokens=result.get("usage", {}).get("output_tokens"),
                latency_ms=latency_ms,
                finish_reason=result.get("stop_reason"),
                raw_response=result,
            )

        except Exception as e:
            logger.exception(f"Anthropic API error: {e}")
            return AIResponse(
                content="",
                model=self.model_name,
                provider=self.provider_type.value,
                error=str(e),
            )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ):
        """Generate streaming response"""
        if not self.api_key:
            yield "API key not configured"
            return

        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        anthropic_messages = []
        for msg in all_messages:
            role = msg["role"]
            if role == "system":
                continue
            if role == "assistant":
                role = "assistant"
            else:
                role = "user"
            anthropic_messages.append({"role": role, "content": msg["content"]})

        data = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system_prompt:
            data["system"] = system_prompt

        data.update(kwargs)

        try:
            client = self._get_client()
            async with client.stream(
                "POST",
                f"{self._base_url}{self.COMPLETIONS_URL}",
                json=data,
            ) as response:
                if response.status_code != 200:
                    error_data = await response.json()
                    yield f"API error: {error_data.get('error', {}).get('message', 'Unknown')}"
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        import json
                        chunk = json.loads(data_str)

                        if chunk.get("type") == "content_block_delta":
                            if chunk.get("delta", {}).get("type") == "text_delta":
                                yield chunk["delta"]["text"]

        except Exception as e:
            logger.exception(f"Anthropic streaming error: {e}")
            yield f"Error: {str(e)}"

    async def count_tokens(self, text: str) -> int:
        """Estimate token count (simplified)"""
        # Rough estimate: ~4 chars per token
        return len(text) // 4 + 1
