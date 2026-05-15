"""
Messages endpoints (standalone).
"""
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bot import Bot
from app.models.session import Session
from app.models.message import Message
from app.schemas.session import MessageResponse, MessageListResponse, MessageFeedback


router = APIRouter()


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get message by ID."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify access
    session_result = await db.execute(
        select(Session).where(Session.id == message.session_id)
    )
    session = session_result.scalar_one_or_none()
    
    bot_result = await db.execute(select(Bot).where(Bot.id == session.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return MessageResponse.model_validate(message)


@router.patch("/{message_id}/feedback", response_model=MessageResponse)
async def rate_message(
    message_id: uuid.UUID,
    feedback: MessageFeedback,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Rate a message (1-5 stars)."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.rating = feedback.rating
    await db.commit()
    await db.refresh(message)
    
    return MessageResponse.model_validate(message)


@router.get("/stats/usage")
async def get_usage_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    bot_id: Optional[uuid.UUID] = None,
):
    """Get message usage statistics."""
    # Build query
    query = select(
        func.count(Message.id).label("total_messages"),
        func.sum(Message.input_tokens).label("total_input_tokens"),
        func.sum(Message.output_tokens).label("total_output_tokens"),
        func.avg(Message.latency_ms).label("avg_latency_ms"),
    ).select_from(Message).join(Session)

    if current_user["role"] != "admin":
        query = query.join(Bot).where(
            Bot.owner_id == uuid.UUID(current_user["id"])
        )
    
    if bot_id:
        query = query.where(Message.session_id.in_(
            select(Session.id).where(Session.bot_id == bot_id)
        ))
    
    result = await db.execute(query)
    stats = result.one()
    
    return {
        "total_messages": stats.total_messages or 0,
        "total_input_tokens": int(stats.total_input_tokens or 0),
        "total_output_tokens": int(stats.total_output_tokens or 0),
        "total_tokens": int((stats.total_input_tokens or 0) + (stats.total_output_tokens or 0)),
        "avg_latency_ms": round(float(stats.avg_latency_ms or 0), 2),
    }
