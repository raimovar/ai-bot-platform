"""
Base Knowledge Store
Abstract interface for knowledge storage backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge with embedding"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    score: float = 0.0


@dataclass
class KnowledgeSource:
    """A source document for knowledge"""
    id: str
    name: str
    source_type: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    status: str = "pending"
    chunk_count: int = 0
    metadata: Dict[str, Any] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseKnowledgeStore(ABC):
    """
    Abstract base class for knowledge storage

    Implementations can use PostgreSQL/pgvector, Qdrant, Chroma, etc.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend"""
        pass

    @abstractmethod
    async def add_source(self, source: KnowledgeSource) -> str:
        """Add a knowledge source"""
        pass

    @abstractmethod
    async def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get a knowledge source by ID"""
        pass

    @abstractmethod
    async def list_sources(self, bot_id: str, limit: int = 100) -> List[KnowledgeSource]:
        """List all sources for a bot"""
        pass

    @abstractmethod
    async def delete_source(self, source_id: str) -> bool:
        """Delete a knowledge source and its chunks"""
        pass

    @abstractmethod
    async def add_chunks(self, source_id: str, chunks: List[KnowledgeChunk]) -> int:
        """Add chunks to a source"""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        bot_id: str,
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[KnowledgeChunk]:
        """
        Search for relevant chunks

        Args:
            query: Search query
            bot_id: Bot ID to search within
            limit: Max results
            threshold: Minimum similarity score

        Returns:
            List of relevant chunks
        """
        pass

    @abstractmethod
    async def get_context(
        self,
        query: str,
        bot_id: str,
        max_chunks: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """
        Get formatted context for RAG

        Args:
            query: Search query
            bot_id: Bot ID
            max_chunks: Max chunks to include
            max_tokens: Max tokens in context

        Returns:
            Formatted context string
        """
        pass

    @abstractmethod
    async def get_stats(self, bot_id: str) -> Dict[str, Any]:
        """Get statistics for a bot's knowledge base"""
        pass

    async def reindex(self, source_id: str) -> int:
        """Re-index a source (delete and re-add chunks)"""
        source = await self.get_source(source_id)
        if not source:
            return 0

        # This should be implemented by subclasses
        # to handle re-chunking and re-embedding
        raise NotImplementedError("Re-indexing not implemented")
