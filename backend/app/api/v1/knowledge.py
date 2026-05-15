"""
Knowledge Base endpoints.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.bot import Bot
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.schemas.knowledge import (
    KnowledgeSourceCreate, KnowledgeSourceUpdate,
    KnowledgeSourceResponse, KnowledgeSourceListResponse,
    KnowledgeChunkResponse, KnowledgeSearchRequest,
    KnowledgeSearchResponse, DocumentUploadResponse,
)


router = APIRouter()

# Allowed file types
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx", ".csv", ".json"}


# ─────────────────────────────────────────────────────────────
# Knowledge Sources
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=KnowledgeSourceListResponse)
async def list_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    bot_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """List knowledge sources."""
    query = select(KnowledgeSource)
    
    if bot_id:
        query = query.where(KnowledgeSource.bot_id == bot_id)
    else:
        # Get sources from user's bots
        bot_query = select(Bot.id).where(
            Bot.owner_id == uuid.UUID(current_user["id"])
        )
        query = query.where(KnowledgeSource.bot_id.in_(bot_query))
    
    if status:
        query = query.where(KnowledgeSource.status == status)
    
    # Count
    count_query = select(func.count(KnowledgeSource.id))
    if bot_id:
        count_query = count_query.where(KnowledgeSource.bot_id == bot_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get page
    query = query.order_by(KnowledgeSource.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    sources = result.scalars().all()
    
    return KnowledgeSourceListResponse(
        items=[KnowledgeSourceResponse.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/", response_model=KnowledgeSourceResponse, status_code=201)
async def create_source(
    source_data: KnowledgeSourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a knowledge source."""
    # Verify bot access - get bot_id from context
    bot_id = getattr(source_data, 'bot_id', None)
    if not bot_id:
        raise HTTPException(status_code=400, detail="bot_id required")
    
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    raise HTTPException(status_code=501, detail="Use POST /knowledge/upload for files")


@router.get("/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get knowledge source by ID."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Verify access
    bot_result = await db.execute(select(Bot).where(Bot.id == source.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return KnowledgeSourceResponse.model_validate(source)


@router.patch("/{source_id}", response_model=KnowledgeSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    source_data: KnowledgeSourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update knowledge source."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Update fields
    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    
    await db.commit()
    await db.refresh(source)
    
    return KnowledgeSourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete knowledge source and all chunks."""
    result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Verify access
    bot_result = await db.execute(select(Bot).where(Bot.id == source.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(source)
    await db.commit()


# ─────────────────────────────────────────────────────────────
# Document Upload
# ─────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    bot_id: uuid.UUID,
    file: UploadFile = File(...),
    name: str = Query(..., min_length=1),
    description: Optional[str] = None,
    chunk_size: int = Query(500, ge=100, le=2000),
    chunk_overlap: int = Query(50, ge=0, le=500),
    db: Annotated[AsyncSession, Depends(get_db)] = Depends(get_db),
    current_user: Annotated[dict, Depends(get_current_user)] = Depends(get_current_user),
):
    """Upload a document to knowledge base."""
    # Verify bot access
    bot_result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = bot_result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check file extension
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file
    content = await file.read()
    file_size = len(content)
    
    # Create source
    source = KnowledgeSource(
        bot_id=bot_id,
        name=name,
        description=description,
        source_type="file",
        file_name=filename,
        file_size=file_size,
        mime_type=file.content_type,
        file_path=f"/tmp/{uuid.uuid4()}_{filename}",  # Will be moved later
        status="pending",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    db.add(source)
    await db.commit()
    await db.refresh(source)
    
    # TODO: Queue for processing (Celery/Redis)
    # For now, just mark as ready (would be async in production)
    source.status = "ready"
    await db.commit()
    
    return DocumentUploadResponse(
        source_id=source.id,
        file_name=filename,
        file_size=file_size,
        status="pending",
        message="Document uploaded. Processing will begin shortly."
    )


# ─────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────

@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Search knowledge base for relevant chunks."""
    # Get user's bot IDs
    bot_query = select(KnowledgeSource.bot_id).join(Bot).where(
        Bot.owner_id == uuid.UUID(current_user["id"])
    )
    
    query = select(KnowledgeChunk).join(KnowledgeSource).where(
        KnowledgeSource.bot_id.in_(bot_query),
        KnowledgeSource.is_active == True,
        KnowledgeSource.status == "ready",
    )
    
    if request.source_ids:
        query = query.where(KnowledgeChunk.source_id.in_(request.source_ids))
    
    # TODO: Use vector search (Qdrant/pgvector)
    # For now, simple text search
    query = query.where(
        KnowledgeChunk.content.ilike(f"%{request.query}%")
    ).limit(request.limit)
    
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    # Get source names
    source_ids = set(c.source_id for c in chunks)
    sources_result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id.in_(source_ids))
    )
    sources = {s.id: s.name for s in sources_result.scalars().all()}
    
    return KnowledgeSearchResponse(
        chunks=[KnowledgeChunkResponse.model_validate(c) for c in chunks],
        sources=sources,
        total=len(chunks),
        query=request.query,
    )


# ─────────────────────────────────────────────────────────────
# Chunks
# ─────────────────────────────────────────────────────────────

@router.get("/{source_id}/chunks", response_model=list[KnowledgeChunkResponse])
async def list_chunks(
    source_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    """List chunks for a source."""
    # Verify access
    source_result = await db.execute(
        select(KnowledgeSource).where(KnowledgeSource.id == source_id)
    )
    source = source_result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    bot_result = await db.execute(select(Bot).where(Bot.id == source.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get chunks
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.source_id == source_id)
        .order_by(KnowledgeChunk.chunk_index)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    chunks = result.scalars().all()
    
    return [KnowledgeChunkResponse.model_validate(c) for c in chunks]
