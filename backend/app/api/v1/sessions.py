"""
Session and message endpoints.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.bot import Bot
from app.models.session import Session
from app.models.message import Message
from app.schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, SessionListResponse,
    MessageCreate, MessageResponse, MessageListResponse,
    ChatRequest, ChatResponse,
)
from app.schemas.bot import BotResponse


router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    bot_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = True,
):
    """List sessions for user's bots."""
    query = select(Session).options(selectinload(Session.messages))
    
    if bot_id:
        query = query.where(Session.bot_id == bot_id)
    else:
        # Get user's bots
        bot_query = select(Bot.id).where(
            Bot.owner_id == uuid.UUID(current_user["id"])
        )
        query = query.where(Session.bot_id.in_(bot_query))
    
    if active_only:
        query = query.where(Session.is_active == True)
    
    # Count
    count_query = select(func.count(Session.id))
    if bot_id:
        count_query = count_query.where(Session.bot_id == bot_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get page
    query = query.order_by(Session.last_message_at.desc().nullsfirst())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Limit messages per session
    items = []
    for s in sessions:
        s_dict = SessionResponse.model_validate(s).model_dump()
        s_dict["recent_messages"] = [
            MessageResponse.model_validate(m)
            for m in s.messages[-10:]  # Last 10 messages
        ]
        items.append(SessionResponse(**s_dict))
    
    return SessionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create or get existing session."""
    # Verify bot access
    result = await db.execute(select(Bot).where(Bot.id == session_data.bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Try to find existing session
    if session_data.external_id:
        result = await db.execute(
            select(Session).where(
                Session.bot_id == session_data.bot_id,
                Session.external_id == session_data.external_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return SessionResponse.model_validate(existing)
    
    # Create new session
    session = Session(
        **session_data.model_dump(exclude={"metadata"}),
        metadata=session_data.metadata or {},
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get session by ID."""
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.messages))
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify access
    bot_result = await db.execute(select(Bot).where(Bot.id == session.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    session_dict = SessionResponse.model_validate(session).model_dump()
    session_dict["recent_messages"] = [
        MessageResponse.model_validate(m)
        for m in session.messages[-50:]
    ]
    
    return SessionResponse(**session_dict)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    session_data: SessionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update session."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update fields
    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    
    await db.commit()
    await db.refresh(session)
    
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete session and all messages."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.delete(session)
    await db.commit()


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    role: Optional[str] = None,
):
    """List messages in a session."""
    # Verify access
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    bot_result = await db.execute(select(Bot).where(Bot.id == session.bot_id))
    bot = bot_result.scalar_one()
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages
    query = select(Message).where(Message.session_id == session_id)
    
    if role:
        query = query.where(Message.role == role)
    
    # Count
    count_query = select(func.count(Message.id)).where(
        Message.session_id == session_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get page
    query = query.order_by(Message.created_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    session_id: uuid.UUID,
    message_data: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add a message to a session."""
    # Verify access
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create message
    message = Message(
        session_id=session_id,
        **message_data.model_dump()
    )
    
    # Update session stats
    session.message_count += 1
    session.last_message_at = datetime.now(timezone.utc)
    
    if message_data.output_tokens:
        session.total_tokens += message_data.output_tokens
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    return MessageResponse.model_validate(message)


# ─────────────────────────────────────────────────────────────
# Chat (Main interaction endpoint)
# ─────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send a message and get AI response."""
    import time
    start_time = time.time()
    
    # Get or create session
    session_result = await db.execute(
        select(Session).where(
            Session.bot_id == request.bot_id,
            Session.external_id == request.external_id
        ) if request.external_id else
        select(Session).where(Session.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        if not request.external_id:
            raise HTTPException(status_code=400, detail="Session not found")
        
        # Create new session
        session = Session(
            bot_id=request.bot_id,
            external_id=request.external_id,
            session_type="telegram" if request.external_id else "web",
            user_name=request.user_name,
            user_id=request.user_id,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
    
    # Save user message
    user_message = Message(
        session_id=session.id,
        role="user",
        content=request.message,
        source=session.session_type,
        metadata=request.metadata,
    )
    db.add(user_message)
    
    session.message_count += 1
    session.last_message_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(session)
    
    # Call bot runtime
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.BOT_RUNTIME_URL}/chat",
                json={
                    "bot_id": str(request.bot_id),
                    "session_id": str(session.id),
                    "message": request.message,
                    "user_name": request.user_name,
                    "user_id": request.user_id,
                }
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI response timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {e}")
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Save assistant response
    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=result["response"],
        model=result.get("model"),
        output_tokens=result.get("tokens_used", 0),
        latency_ms=latency_ms,
        source=session.session_type,
    )
    db.add(assistant_message)
    
    session.total_tokens += result.get("tokens_used", 0)
    
    # Update bot stats
    bot_result = await db.execute(select(Bot).where(Bot.id == request.bot_id))
    bot = bot_result.scalar_one()
    bot.total_messages += 1
    bot.total_tokens_used += result.get("tokens_used", 0)
    
    await db.commit()
    await db.refresh(assistant_message)
    await db.refresh(session)
    
    return ChatResponse(
        session_id=session.id,
        message_id=assistant_message.id,
        response=result["response"],
        model=result.get("model", bot.model_name),
        tokens_used=result.get("tokens_used", 0),
        latency_ms=latency_ms,
        session=SessionResponse.model_validate(session),
    )
