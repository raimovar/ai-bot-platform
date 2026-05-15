"""
Knowledge Storage Backends
PostgreSQL/pgvector and Qdrant implementations
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
import httpx

from .base import BaseKnowledgeStore, KnowledgeChunk, KnowledgeSource
from .embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class PostgresKnowledgeStore(BaseKnowledgeStore):
    """
    PostgreSQL with pgvector for knowledge storage

    Requires pgvector extension.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_provider: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_dimensions: int = 1536,
    ):
        super().__init__()

        self.db = db_session
        self.embedding_service = get_embedding_service()

        if embedding_provider:
            self.embedding_service.configure_provider(
                provider_type=embedding_provider,
                api_key=embedding_api_key,
                base_url=embedding_base_url,
                model=embedding_model,
            )

        self.embedding_dimensions = embedding_dimensions

    async def connect(self) -> None:
        """Initialize connection"""
        pass

    async def disconnect(self) -> None:
        """Close connection"""
        await self.db.close()

    async def add_source(self, source: KnowledgeSource) -> str:
        """Add a knowledge source"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel

        model = KnowledgeSourceModel(
            id=uuid.UUID(source.id),
            bot_id=uuid.UUID(source.metadata.get("bot_id")),
            name=source.name,
            source_type=source.source_type,
            file_path=source.file_path,
            url=source.url,
            status=source.status,
            metadata=source.metadata,
        )

        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)

        return str(model.id)

    async def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get a knowledge source by ID"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel

        result = await self.db.execute(
            select(KnowledgeSourceModel).where(KnowledgeSourceModel.id == uuid.UUID(source_id))
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return KnowledgeSource(
            id=str(model.id),
            name=model.name,
            source_type=model.source_type,
            file_path=model.file_path,
            url=model.url,
            status=model.status,
            chunk_count=model.chunk_count or 0,
            metadata=model.metadata or {},
            created_at=model.created_at.isoformat() if model.created_at else None,
        )

    async def list_sources(self, bot_id: str, limit: int = 100) -> List[KnowledgeSource]:
        """List all sources for a bot"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel

        result = await self.db.execute(
            select(KnowledgeSourceModel)
            .where(KnowledgeSourceModel.bot_id == uuid.UUID(bot_id))
            .limit(limit)
        )
        models = result.scalars().all()

        return [
            KnowledgeSource(
                id=str(m.id),
                name=m.name,
                source_type=m.source_type,
                file_path=m.file_path,
                url=m.url,
                status=m.status,
                chunk_count=m.chunk_count or 0,
                metadata=m.metadata or {},
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in models
        ]

    async def delete_source(self, source_id: str) -> bool:
        """Delete a knowledge source and its chunks"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel
        from app.models.knowledge import KnowledgeChunk as KnowledgeChunkModel

        # Delete chunks first
        await self.db.execute(
            delete(KnowledgeChunkModel).where(KnowledgeChunkModel.source_id == uuid.UUID(source_id))
        )

        # Delete source
        result = await self.db.execute(
            delete(KnowledgeSourceModel).where(KnowledgeSourceModel.id == uuid.UUID(source_id))
        )

        await self.db.commit()
        return result.rowcount > 0

    async def add_chunks(self, source_id: str, chunks: List[KnowledgeChunk]) -> int:
        """Add chunks with embeddings"""
        from app.models.knowledge import KnowledgeChunk as KnowledgeChunkModel
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel

        if not chunks:
            return 0

        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = await self.embedding_service.embed(texts)

        # Insert chunks
        for chunk, embedding in zip(chunks, embeddings):
            model = KnowledgeChunkModel(
                id=uuid.uuid4(),
                source_id=uuid.UUID(source_id),
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
            )
            self.db.add(model)

        # Update source chunk count
        await self.db.execute(
            select(KnowledgeSourceModel).where(KnowledgeSourceModel.id == uuid.UUID(source_id))
        )
        result = await self.db.execute(
            select(KnowledgeSourceModel).where(KnowledgeSourceModel.id == uuid.UUID(source_id))
        )
        source = result.scalar_one_or_none()
        if source:
            source.chunk_count = (source.chunk_count or 0) + len(chunks)
            source.status = "ready"

        await self.db.commit()
        return len(chunks)

    async def search(
        self,
        query: str,
        bot_id: str,
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[KnowledgeChunk]:
        """Search for relevant chunks"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel
        from app.models.knowledge import KnowledgeChunk as KnowledgeChunkModel

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)

        # Search with pgvector
        # Note: This requires pgvector extension
        result = await self.db.execute(
            select(
                KnowledgeChunkModel,
                KnowledgeChunkModel.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(KnowledgeSourceModel, KnowledgeChunkModel.source_id == KnowledgeSourceModel.id)
            .where(KnowledgeSourceModel.bot_id == uuid.UUID(bot_id))
            .where(KnowledgeSourceModel.status == "ready")
            .order_by("distance")
            .limit(limit)
        )

        chunks = []
        for row in result.all():
            chunk_model = row[0]
            distance = row[1]
            score = 1 - distance  # Convert distance to similarity

            if score >= threshold:
                chunks.append(KnowledgeChunk(
                    id=str(chunk_model.id),
                    content=chunk_model.content,
                    metadata=chunk_model.metadata or {},
                    embedding=chunk_model.embedding,
                    score=score,
                ))

        return chunks

    async def get_context(
        self,
        query: str,
        bot_id: str,
        max_chunks: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """Get formatted context for RAG"""
        chunks = await self.search(query, bot_id, limit=max_chunks)

        context_parts = []
        total_tokens = 0

        for chunk in chunks:
            # Rough token estimate: ~4 chars per token
            chunk_tokens = len(chunk.content) // 4

            if total_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk.content)
            total_tokens += chunk_tokens

        if not context_parts:
            return ""

        # Format as context
        context = "\n\n---\n\n".join(context_parts)
        return f"Relevant information:\n\n{context}\n\nUse this information to answer the user\'s question."

    async def get_stats(self, bot_id: str) -> Dict[str, Any]:
        """Get statistics for a bot\'s knowledge base"""
        from app.models.knowledge import KnowledgeSource as KnowledgeSourceModel
        from app.models.knowledge import KnowledgeChunk as KnowledgeChunkModel

        # Count sources
        sources_result = await self.db.execute(
            select(func.count()).select_from(KnowledgeSourceModel)
            .where(KnowledgeSourceModel.bot_id == uuid.UUID(bot_id))
        )
        source_count = sources_result.scalar()

        # Count chunks
        chunks_result = await self.db.execute(
            select(func.count()).select_from(KnowledgeChunkModel)
            .join(KnowledgeSourceModel, KnowledgeChunkModel.source_id == KnowledgeSourceModel.id)
            .where(KnowledgeSourceModel.bot_id == uuid.UUID(bot_id))
        )
        chunk_count = chunks_result.scalar()

        return {
            "source_count": source_count or 0,
            "chunk_count": chunk_count or 0,
            "embedding_dimensions": self.embedding_dimensions,
        }


class QdrantKnowledgeStore(BaseKnowledgeStore):
    """
    Qdrant vector database for knowledge storage

    Alternative to pgvector with better scalability.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:6333",
        collection_name: str = "knowledge",
        embedding_provider: str = "openai",
        embedding_api_key: Optional[str] = None,
        embedding_dimensions: int = 1536,
    ):
        super().__init__()

        self.base_url = base_url.rstrip("/")
        self.collection_name = collection_name
        self.embedding_service = get_embedding_service()
        self.embedding_dimensions = embedding_dimensions

        if embedding_api_key:
            self.embedding_service.configure_provider(
                provider_type=embedding_provider,
                api_key=embedding_api_key,
            )

        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Connect to Qdrant"""
        self._client = httpx.AsyncClient(timeout=30.0)

        # Create collection if not exists
        await self._ensure_collection()

    async def disconnect(self) -> None:
        """Disconnect from Qdrant"""
        if self._client:
            await self._client.aclose()

    async def _ensure_collection(self):
        """Ensure collection exists"""
        response = await self._client.get(
            f"{self.base_url}/collections/{self.collection_name}"
        )

        if response.status_code == 404:
            # Create collection
            await self._client.put(
                f"{self.base_url}/collections/{self.collection_name}",
                json={
                    "vectors": {
                        "size": self.embedding_dimensions,
                        "distance": "Cosine",
                    }
                },
            )

    async def _ensure_client(self):
        if not self._client:
            await self.connect()

    async def add_source(self, source: KnowledgeSource) -> str:
        """Add a knowledge source"""
        source_id = source.id or str(uuid.uuid4())
        return source_id

    async def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get a knowledge source (Qdrant doesn\'t store sources directly)"""
        return None

    async def list_sources(self, bot_id: str, limit: int = 100) -> List[KnowledgeSource]:
        """List sources (limited in Qdrant)"""
        return []

    async def delete_source(self, source_id: str) -> bool:
        """Delete source chunks"""
        await self._ensure_client()

        response = await self._client.post(
            f"{self.base_url}/collections/{self.collection_name}/points/delete",
            json={
                "filter": {
                    "must": [
                        {"key": "source_id", "match": {"value": source_id}}
                    ]
                }
            },
        )

        return response.status_code == 200

    async def add_chunks(self, source_id: str, chunks: List[KnowledgeChunk]) -> int:
        """Add chunks with embeddings"""
        await self._ensure_client()

        if not chunks:
            return 0

        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = await self.embedding_service.embed(texts)

        # Prepare points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "source_id": source_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "chunk_index": i,
                },
            })

        # Upload to Qdrant
        response = await self._client.put(
            f"{self.base_url}/collections/{self.collection_name}/points",
            json={"points": points},
        )

        return len(points) if response.status_code == 200 else 0

    async def search(
        self,
        query: str,
        bot_id: str,
        limit: int = 5,
        threshold: float = 0.0,
    ) -> List[KnowledgeChunk]:
        """Search for relevant chunks"""
        await self._ensure_client()

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)

        # Search in Qdrant
        response = await self._client.post(
            f"{self.base_url}/collections/{self.collection_name}/points/search",
            json={
                "vector": query_embedding,
                "limit": limit,
                "score_threshold": threshold,
                "filter": {
                    "must": [
                        {"key": "bot_id", "match": {"value": bot_id}}
                    ]
                },
            },
        )

        if response.status_code != 200:
            return []

        results = response.json().get("result", [])

        return [
            KnowledgeChunk(
                id=r["id"],
                content=r["payload"]["content"],
                metadata=r["payload"].get("metadata", {}),
                score=r["score"],
            )
            for r in results
        ]

    async def get_context(
        self,
        query: str,
        bot_id: str,
        max_chunks: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """Get formatted context for RAG"""
        chunks = await self.search(query, bot_id, limit=max_chunks)

        context_parts = []
        total_tokens = 0

        for chunk in chunks:
            chunk_tokens = len(chunk.content) // 4
            if total_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(chunk.content)
            total_tokens += chunk_tokens

        if not context_parts:
            return ""

        context = "\n\n---\n\n".join(context_parts)
        return f"Relevant information:\n\n{context}\n\nUse this information to answer the user\'s question."

    async def get_stats(self, bot_id: str) -> Dict[str, Any]:
        """Get statistics"""
        await self._ensure_client()

        response = await self._client.get(
            f"{self.base_url}/collections/{self.collection_name}"
        )

        if response.status_code != 200:
            return {"error": "Failed to get stats"}

        info = response.json().get("result", {})

        return {
            "vectors_count": info.get("vectors_count", 0),
            "points_count": info.get("points_count", 0),
            "embedding_dimensions": self.embedding_dimensions,
        }
