"""
Knowledge Retriever
Retrieve relevant knowledge for RAG
"""

import logging
from typing import List, Dict, Any, Optional
from .base import KnowledgeChunk, BaseKnowledgeStore
from .embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Retrieve knowledge for RAG queries

    Usage:
        retriever = KnowledgeRetriever(knowledge_store)

        # Get relevant context
        context = await retriever.get_context(
            query="What is Python?",
            bot_id="bot-123",
            max_chunks=5,
        )

        # Or get raw chunks
        chunks = await retriever.retrieve(
            query="Python tutorials",
            bot_id="bot-123",
            limit=10,
        )
    """

    def __init__(
        self,
        knowledge_store: BaseKnowledgeStore,
        embedding_service: Optional[Any] = None,
    ):
        self.store = knowledge_store
        self.embedding_service = embedding_service or get_embedding_service()

    async def retrieve(
        self,
        query: str,
        bot_id: str,
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[KnowledgeChunk]:
        """
        Retrieve relevant chunks for a query

        Args:
            query: Search query
            bot_id: Bot ID to search within
            limit: Max results
            threshold: Min similarity score

        Returns:
            List of relevant chunks
        """
        return await self.store.search(
            query=query,
            bot_id=bot_id,
            limit=limit,
            threshold=threshold,
        )

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
        return await self.store.get_context(
            query=query,
            bot_id=bot_id,
            max_chunks=max_chunks,
            max_tokens=max_tokens,
        )

    async def rerank(
        self,
        chunks: List[KnowledgeChunk],
        query: str,
        top_k: int = 3,
    ) -> List[KnowledgeChunk]:
        """
        Re-rank chunks using a more sophisticated method

        Simple implementation: just return top-k by score
        Advanced: use cross-encoder, MMR, etc.
        """
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
        return sorted_chunks[:top_k]

    async def mmr(
        self,
        chunks: List[KnowledgeChunk],
        query: str,
        diversity: float = 0.5,
        top_k: int = 3,
    ) -> List[KnowledgeChunk]:
        """
        Maximal Marginal Relevance for diverse results

        Balances relevance with diversity.

        Args:
            chunks: Candidate chunks
            query: Search query
            diversity: Higher = more diverse (0-1)
            top_k: Number of results

        Returns:
            Diverse set of relevant chunks
        """
        if not chunks or top_k >= len(chunks):
            return chunks[:top_k]

        # Simple MMR: sort by score - diversity * rank
        result = []
        used_indices = set()

        for i, chunk in enumerate(chunks):
            mmr_score = chunk.score - diversity * (i / len(chunks))
            chunk.metadata["mmr_score"] = mmr_score

        sorted_by_mmr = sorted(chunks, key=lambda c: c.metadata.get("mmr_score", 0), reverse=True)

        return sorted_by_mmr[:top_k]
