"""
Knowledge API Endpoints
Manage knowledge bases for bots
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bot import Bot
from app.models.user import User
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.schemas.bot import BotResponse
from app.knowledge import (
    DocumentProcessor,
    get_embedding_service,
    KnowledgeRetriever,
    PostgresKnowledgeStore,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# Schemas
class KnowledgeSourceCreate(BaseModel):
    name: str
    source_type: str  # file, url, text
    content: Optional[str] = None
    url: Optional[str] = None


class KnowledgeSourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    status: str
    chunk_count: int
    metadata: dict


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = 5


class KnowledgeSearchResponse(BaseModel):
    chunks: List[dict]
    context: str


# Endpoints
@router.get("/bots/{bot_id}/sources", response_model=List[KnowledgeSourceResponse])
async def list_knowledge_sources(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all knowledge sources for a bot"""
    result = await db.execute(
        select(KnowledgeSource)
        .where(KnowledgeSource.bot_id == bot_id)
        .order_by(KnowledgeSource.created_at.desc())
    )
    sources = result.scalars().all()

    return [
        KnowledgeSourceResponse(
            id=str(s.id),
            name=s.name,
            source_type=s.source_type,
            status=s.status,
            chunk_count=s.chunk_count or 0,
            metadata=s.metadata or {},
        )
        for s in sources
    ]


@router.post("/bots/{bot_id}/sources")
async def create_knowledge_source(
    bot_id: int,
    source: KnowledgeSourceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new knowledge source and process it"""
    # Verify bot ownership
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Create source
    knowledge_source = KnowledgeSource(
        bot_id=bot_id,
        name=source.name,
        source_type=source.source_type,
        url=source.url,
        status="pending",
        metadata={"created_by": str(current_user.id)},
    )

    db.add(knowledge_source)
    await db.commit()
    await db.refresh(knowledge_source)

    # Process in background
    if source.source_type == "text" and source.content:
        background_tasks.add_task(
            process_text_source,
            str(knowledge_source.id),
            source.content,
        )
    elif source.source_type == "url" and source.url:
        background_tasks.add_task(
            process_url_source,
            str(knowledge_source.id),
            source.url,
        )

    return {
        "id": str(knowledge_source.id),
        "name": knowledge_source.name,
        "status": knowledge_source.status,
    }


@router.post("/bots/{bot_id}/sources/upload")
async def upload_knowledge_file(
    bot_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file as knowledge source"""
    # Verify bot ownership
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Save file
    import os
    from pathlib import Path

    upload_dir = Path("/tmp/knowledge_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{bot_id}_{file.filename}"

    content = await file.read()
    file_path.write_bytes(content)

    # Create source
    knowledge_source = KnowledgeSource(
        bot_id=bot_id,
        name=file.filename,
        source_type="file",
        file_path=str(file_path),
        status="pending",
        metadata={"created_by": str(current_user.id)},
    )

    db.add(knowledge_source)
    await db.commit()
    await db.refresh(knowledge_source)

    # Process in background
    if background_tasks:
        background_tasks.add_task(
            process_file_source,
            str(knowledge_source.id),
            str(file_path),
        )

    return {
        "id": str(knowledge_source.id),
        "name": knowledge_source.name,
        "status": knowledge_source.status,
    }


@router.delete("/bots/{bot_id}/sources/{source_id}")
async def delete_knowledge_source(
    bot_id: int,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a knowledge source"""
    result = await db.execute(
        select(KnowledgeSource)
        .where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.bot_id == bot_id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()

    return {"ok": True}


@router.post("/bots/{bot_id}/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    bot_id: int,
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search knowledge base for a bot"""
    # Create store
    store = PostgresKnowledgeStore(db)

    # Create retriever
    retriever = KnowledgeRetriever(store)

    # Search
    chunks = await retriever.retrieve(
        query=request.query,
        bot_id=str(bot_id),
        limit=request.limit,
    )

    # Get formatted context
    context = await retriever.get_context(
        query=request.query,
        bot_id=str(bot_id),
        max_chunks=request.limit,
    )

    return KnowledgeSearchResponse(
        chunks=[
            {
                "id": c.id,
                "content": c.content,
                "score": c.score,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
        context=context,
    )


@router.get("/bots/{bot_id}/stats")
async def get_knowledge_stats(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge base statistics"""
    # Count sources
    sources_result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.bot_id == bot_id)
    )
    sources = sources_result.scalars().all()

    total_chunks = sum(s.chunk_count or 0 for s in sources)

    return {
        "source_count": len(sources),
        "chunk_count": total_chunks,
        "sources": [
            {
                "id": str(s.id),
                "name": s.name,
                "status": s.status,
                "chunk_count": s.chunk_count or 0,
            }
            for s in sources
        ],
    }


# Background processing functions
async def process_text_source(source_id: str, content: str):
    """Process text content into chunks"""
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            # Update status
            result = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == source_id)
            )
            source = result.scalar_one_or_none()
            if not source:
                return

            source.status = "indexing"
            await db.commit()

            # Process text
            processor = DocumentProcessor()
            chunks = processor.process_text(content, metadata={"source_id": source_id})

            # Create store and add chunks
            store = PostgresKnowledgeStore(db)
            from app.knowledge.base import KnowledgeChunk

            kb_chunks = [
                KnowledgeChunk(
                    id=f"{source_id}_{i}",
                    content=c.content,
                    metadata={**c.metadata, "source_id": source_id},
                )
                for i, c in enumerate(chunks)
            ]

            await store.add_chunks(source_id, kb_chunks)

            # Update source
            source.chunk_count = len(kb_chunks)
            source.total_chars = len(content)
            source.status = "ready"
            await db.commit()

            logger.info(f"Processed text source {source_id}: {len(kb_chunks)} chunks")

        except Exception as e:
            logger.exception(f"Failed to process text source {source_id}")
            source.status = "error"
            source.error_message = str(e)
            await db.commit()


async def process_file_source(source_id: str, file_path: str):
    """Process a file into chunks"""
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == source_id)
            )
            source = result.scalar_one_or_none()
            if not source:
                return

            source.status = "indexing"
            await db.commit()

            # Process file
            processor = DocumentProcessor()
            chunks = processor.process_file(file_path)

            # Create store and add chunks
            store = PostgresKnowledgeStore(db)
            from app.knowledge.base import KnowledgeChunk

            kb_chunks = [
                KnowledgeChunk(
                    id=f"{source_id}_{i}",
                    content=c.content,
                    metadata={**c.metadata, "source_id": source_id},
                )
                for i, c in enumerate(chunks)
            ]

            await store.add_chunks(source_id, kb_chunks)

            # Update source
            source.chunk_count = len(kb_chunks)
            source.status = "ready"
            await db.commit()

            logger.info(f"Processed file source {source_id}: {len(kb_chunks)} chunks")

        except Exception as e:
            logger.exception(f"Failed to process file source {source_id}")
            source.status = "error"
            source.error_message = str(e)
            await db.commit()


async def process_url_source(source_id: str, url: str):
    """Process URL content into chunks"""
    from app.core.database import async_session_maker
    import httpx

    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == source_id)
            )
            source = result.scalar_one_or_none()
            if not source:
                return

            source.status = "indexing"
            await db.commit()

            # Fetch URL
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                html_content = response.text

            # Process HTML
            processor = DocumentProcessor()
            chunks = processor.process_url(url, html_content)

            # Create store and add chunks
            store = PostgresKnowledgeStore(db)
            from app.knowledge.base import KnowledgeChunk

            kb_chunks = [
                KnowledgeChunk(
                    id=f"{source_id}_{i}",
                    content=c.content,
                    metadata={**c.metadata, "source_id": source_id},
                )
                for i, c in enumerate(chunks)
            ]

            await store.add_chunks(source_id, kb_chunks)

            # Update source
            source.chunk_count = len(kb_chunks)
            source.status = "ready"
            await db.commit()

            logger.info(f"Processed URL source {source_id}: {len(kb_chunks)} chunks")

        except Exception as e:
            logger.exception(f"Failed to process URL source {source_id}")
            source.status = "error"
            source.error_message = str(e)
            await db.commit()
