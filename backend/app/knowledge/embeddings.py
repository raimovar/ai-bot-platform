"""
Embedding Service
Generate embeddings for text using various providers
"""

import logging
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import httpx

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base for embedding providers"""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding dimensions"""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI text-embedding-3 models"""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self.dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    @property
    def dimensions(self) -> int:
        return self.dimensions_map.get(self.model, 1536)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": self.model,
                },
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.text}")

            result = response.json()
            return [item["embedding"] for item in result["data"]]

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        embeddings = await self.embed([text])
        return embeddings[0]


class OllamaEmbedder(BaseEmbedder):
    """Ollama local embeddings"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.base_url = base_url
        self.model = model
        self.dimensions = 768  # nomic-embed-text default

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            embeddings = []
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"prompt": text, "model": self.model},
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.text}")

                result = response.json()
                embeddings.append(result["embedding"])

            return embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        return (await self.embed([text]))[0]


class HuggingFaceEmbedder(BaseEmbedder):
    """HuggingFace sentence transformers"""

    def __init__(self, api_token: str, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.api_token = api_token
        self.model = model
        self.dimensions = 384  # MiniLM default

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using HuggingFace API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={"inputs": texts},
            )

            if response.status_code != 200:
                raise Exception(f"HuggingFace API error: {response.text}")

            return response.json()

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        return (await self.embed([text]))[0]


class EmbeddingService:
    """
    Unified embedding service

    Usage:
        service = EmbeddingService()

        # Configure provider
        service.configure_provider("openai", api_key="sk-...")

        # Or use Ollama
        service.configure_provider("ollama", base_url="http://localhost:11434")

        # Generate embeddings
        embeddings = await service.embed(["Hello world", "How are you?"])
    """

    def __init__(self):
        self._provider: Optional[BaseEmbedder] = None
        self._provider_type: Optional[str] = None

    def configure_provider(
        self,
        provider_type: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Configure the embedding provider"""
        if provider_type in ["openai", "openai-embeddings"]:
            self._provider = OpenAIEmbedder(
                api_key=api_key or "",
                model=model or "text-embedding-3-small",
            )
        elif provider_type == "ollama":
            self._provider = OllamaEmbedder(
                base_url=base_url or "http://localhost:11434",
                model=model or "nomic-embed-text",
            )
        elif provider_type in ["huggingface", "hf"]:
            self._provider = HuggingFaceEmbedder(
                api_token=api_key or "",
                model=model or "sentence-transformers/all-MiniLM-L6-v2",
            )
        else:
            raise ValueError(f"Unknown embedding provider: {provider_type}")

        self._provider_type = provider_type

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        if not self._provider:
            raise RuntimeError("Embedding provider not configured")
        return await self._provider.embed(texts)

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        if not self._provider:
            raise RuntimeError("Embedding provider not configured")
        return await self._provider.embed_query(text)

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions"""
        if not self._provider:
            raise RuntimeError("Embedding provider not configured")
        return self._provider.dimensions

    @property
    def provider_type(self) -> Optional[str]:
        """Get current provider type"""
        return self._provider_type


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
