"""
OpenAI Provider
OpenAI API integration
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

from .base import BaseAIProvider, AIResponse, ProviderType

logger = logging.getLogger(__name__)

# Model context windows
MODEL_CONTEXT_WINDOWS = {
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
}


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI API provider

    Supports GPT-4, GPT-3.5 Turbo, and compatible models.
    """

    BASE_URL = "https://api.openai.com/v1"
    CHAT_COMPLETIONS = "/chat/completions"

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name, api_key, base_url, config)
        self._base_url = base_url or self.BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def context_window(self) -> int:
        """Get context window based on model"""
        # Check exact match
        if self.model_name in MODEL_CONTEXT_WINDOWS:
            return MODEL_CONTEXT_WINDOWS[self.model_name]

        # Check prefix match
        for prefix, window in MODEL_CONTEXT_WINDOWS.items():
            if self.model_name.startswith(prefix):
                return window

        # Default
        return 16385

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=120.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
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
        """Generate response from OpenAI"""
        if not self.api_key:
            return AIResponse(
                content="",
                model=self.model_name,
                provider=self.provider_type.value,
                error="API key not configured",
            )

        # Build messages with system prompt
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        # Build request
        data = {
            "model": self.model_name,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if top_p:
            data["top_p"] = top_p
        if stop:
            data["stop"] = stop

        data.update(kwargs)

        try:
            client = self._get_client()
            start_time = asyncio.get_event_loop().time()

            response = await client.post(
                f"{self._base_url}{self.CHAT_COMPLETIONS}",
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
                content=result["choices"][0]["message"]["content"],
                model=result.get("model", self.model_name),
                provider=self.provider_type.value,
                tokens_used=result.get("usage", {}).get("total_tokens"),
                prompt_tokens=result.get("usage", {}).get("prompt_tokens"),
                completion_tokens=result.get("usage", {}).get("completion_tokens"),
                latency_ms=latency_ms,
                finish_reason=result["choices"][0].get("finish_reason"),
                raw_response=result,
            )

        except Exception as e:
            logger.exception(f"OpenAI API error: {e}")
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

        data = {
            "model": self.model_name,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        data.update(kwargs)

        try:
            client = self._get_client()
            async with client.stream(
                "POST",
                f"{self._base_url}{self.CHAT_COMPLETIONS}",
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
                        content = chunk["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            yield content

        except Exception as e:
            logger.exception(f"OpenAI streaming error: {e}")
            yield f"Error: {str(e)}"

    async def count_tokens(self, text: str) -> int:
        """Estimate token count (simplified)"""
        # Rough estimate: ~4 chars per token
        return len(text) // 4 + 1
