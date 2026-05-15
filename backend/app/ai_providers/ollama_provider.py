"""
Ollama Provider
Ollama local LLM integration
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

from .base import BaseAIProvider, AIResponse, ProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(BaseAIProvider):
    """
    Ollama local LLM provider

    Supports all Ollama-compatible models running locally.
    """

    BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model_name: str = "llama3.2",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(model_name, api_key, base_url, config)
        self._base_url = base_url or self.BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def context_window(self) -> int:
        # Ollama models typically have 4k-128k context
        return 4096

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=300.0,  # Longer timeout for local models
                base_url=self._base_url,
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
        """Generate response from Ollama"""
        # Build prompt from messages
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.capitalize()}: {content}")

        prompt_parts.append("Assistant:")
        prompt = "\n\n".join(prompt_parts)

        # Build request
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if top_p:
            data["options"]["top_p"] = top_p
        if stop:
            data["options"]["stop"] = stop

        data.update(kwargs)

        try:
            client = self._get_client()
            start_time = asyncio.get_event_loop().time()

            response = await client.post("/api/generate", json=data)
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            if response.status_code != 200:
                return AIResponse(
                    content="",
                    model=self.model_name,
                    provider=self.provider_type.value,
                    error=f"Ollama error {response.status_code}: {response.text}",
                )

            result = response.json()

            return AIResponse(
                content=result.get("response", ""),
                model=self.model_name,
                provider=self.provider_type.value,
                tokens_used=result.get("eval_count"),
                prompt_tokens=result.get("prompt_eval_count"),
                latency_ms=latency_ms,
                raw_response=result,
            )

        except httpx.ConnectError:
            return AIResponse(
                content="",
                model=self.model_name,
                provider=self.provider_type.value,
                error="Cannot connect to Ollama. Is it running?",
            )
        except Exception as e:
            logger.exception(f"Ollama error: {e}")
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
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.capitalize()}: {content}")

        prompt_parts.append("Assistant:")
        prompt = "\n\n".join(prompt_parts)

        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        data.update(kwargs)

        try:
            client = self._get_client()
            async with client.stream("POST", "/api/generate", json=data) as response:
                if response.status_code != 200:
                    yield f"Ollama error: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    import json
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("response", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            yield "Cannot connect to Ollama. Is it running?"
        except Exception as e:
            logger.exception(f"Ollama streaming error: {e}")
            yield f"Error: {str(e)}"

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models in Ollama"""
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            if response.status_code == 200:
                return response.json().get("models", [])
            return []
        except Exception:
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            client = self._get_client()
            async with client.stream(
                "POST",
                "/api/pull",
                json={"name": model_name},
            ) as response:
                return response.status_code == 200
        except Exception:
            return False

    async def count_tokens(self, text: str) -> int:
        """Estimate token count (simplified)"""
        return len(text) // 4 + 1

    async def validate_config(self) -> bool:
        """Check if Ollama is accessible"""
        try:
            client = self._get_client()
            response = await client.get("/")
            return response.status_code == 200
        except Exception:
            return False
