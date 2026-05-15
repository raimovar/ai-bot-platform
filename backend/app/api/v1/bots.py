"""
Bot management endpoints.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_admin
from app.models.bot import Bot, BotTool
from app.models.user import User
from app.schemas.bot import (
    BotCreate, BotUpdate, BotResponse, BotListResponse,
    BotConfig, BotToolCreate, BotToolUpdate, BotToolResponse,
    BotStartRequest, BotStopRequest, BotStatsResponse,
)
from app.services.bot_service import BotService


router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Bot CRUD
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=BotListResponse)
async def list_bots(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
):
    """List bots for current user."""
    query = select(Bot).options(selectinload(Bot.tools))
    
    # Filter by owner or public
    if current_user["role"] != "admin":
        query = query.where(
            or_(
                Bot.owner_id == uuid.UUID(current_user["id"]),
                Bot.is_public == True
            )
        )
    
    if status_filter:
        query = query.where(Bot.status == status_filter)
    
    if search:
        query = query.where(
            Bot.name.ilike(f"%{search}%") |
            Bot.description.ilike(f"%{search}%")
        )
    
    # Count total
    count_query = select(func.count(Bot.id))
    if current_user["role"] != "admin":
        count_query = count_query.where(
            or_(
                Bot.owner_id == uuid.UUID(current_user["id"]),
                Bot.is_public == True
            )
        )
    if status_filter:
        count_query = count_query.where(Bot.status == status_filter)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get page
    query = query.order_by(Bot.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    bots = result.scalars().all()
    
    return BotListResponse(
        items=[BotResponse.model_validate(b) for b in bots],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/", response_model=BotResponse, status_code=201)
async def create_bot(
    bot_data: BotCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new bot."""
    # Check bot limit
    if current_user["role"] != "admin":
        result = await db.execute(
            select(func.count(Bot.id)).where(
                Bot.owner_id == uuid.UUID(current_user["id"])
            )
        )
        bot_count = result.scalar()
        
        user_result = await db.execute(
            select(User).where(User.id == uuid.UUID(current_user["id"]))
        )
        user = user_result.scalar_one()
        
        if bot_count >= user.max_bots:
            raise HTTPException(
                status_code=403,
                detail=f"Bot limit reached ({user.max_bots})"
            )
    
    # Check slug uniqueness
    result = await db.execute(
        select(Bot).where(Bot.slug == bot_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Bot slug already exists"
        )
    
    # Create bot
    bot = Bot(
        **bot_data.model_dump(),
        owner_id=uuid.UUID(current_user["id"]),
    )
    
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    
    return BotResponse.model_validate(bot)


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get bot by ID."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.tools))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check access
    if not bot.is_public and str(bot.owner_id) != current_user["id"]:
        if current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
    
    return BotResponse.model_validate(bot)


@router.patch("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: uuid.UUID,
    bot_data: BotUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update bot configuration."""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.tools))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check ownership
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your bot")
    
    # Update fields
    update_data = bot_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bot, field, value)
    
    bot.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(bot)
    
    return BotResponse.model_validate(bot)


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete bot and all associated data."""
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check ownership
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your bot")
    
    await db.delete(bot)
    await db.commit()


# ─────────────────────────────────────────────────────────────
# Bot Lifecycle (Start/Stop)
# ─────────────────────────────────────────────────────────────

@router.post("/{bot_id}/start", response_model=BotResponse)
async def start_bot(
    bot_id: uuid.UUID,
    request: BotStartRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Start a bot."""
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check ownership
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your bot")
    
    if bot.status == "running":
        raise HTTPException(status_code=400, detail="Bot already running")
    
    # Update Telegram token if provided
    if request.telegram_token:
        bot.telegram_token = request.telegram_token
    
    # Update status
    bot.status = "starting"
    bot.is_active = True
    bot.last_started = datetime.now(timezone.utc)
    bot.last_error = None
    
    await db.commit()
    
    # Notify bot runtime to start
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.BOT_RUNTIME_URL}/bots/{bot_id}/start",
                timeout=5.0
            )
    except Exception as e:
        bot.status = "error"
        bot.last_error = str(e)
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bot: {e}"
        )
    
    bot.status = "running"
    await db.commit()
    await db.refresh(bot)
    
    return BotResponse.model_validate(bot)


@router.post("/{bot_id}/stop", response_model=BotResponse)
async def stop_bot(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Stop a bot."""
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Check ownership
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your bot")
    
    if bot.status == "stopped":
        raise HTTPException(status_code=400, detail="Bot already stopped")
    
    # Notify bot runtime to stop
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.BOT_RUNTIME_URL}/bots/{bot_id}/stop",
                timeout=5.0
            )
    except Exception as e:
        print(f"Failed to stop bot gracefully: {e}")
    
    bot.status = "stopped"
    bot.is_active = False
    
    await db.commit()
    await db.refresh(bot)
    
    return BotResponse.model_validate(bot)


@router.post("/{bot_id}/restart", response_model=BotResponse)
async def restart_bot(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Restart a bot."""
    # Stop first
    await stop_bot(bot_id, db, current_user)
    
    # Start again
    return await start_bot(
        bot_id,
        BotStartRequest(),
        BackgroundTasks(),
        db,
        current_user
    )


# ─────────────────────────────────────────────────────────────
# Bot Config (for runtime)
# ─────────────────────────────────────────────────────────────

@router.get("/{bot_id}/config", response_model=BotConfig)
async def get_bot_config(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get bot configuration for runtime (internal use)."""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return BotConfig.model_validate(bot)


# ─────────────────────────────────────────────────────────────
# Bot Tools
# ─────────────────────────────────────────────────────────────

@router.post("/{bot_id}/tools", response_model=BotToolResponse, status_code=201)
async def add_bot_tool(
    bot_id: uuid.UUID,
    tool_data: BotToolCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add a tool to a bot."""
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if str(bot.owner_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your bot")
    
    # Check if tool already exists
    result = await db.execute(
        select(BotTool).where(
            BotTool.bot_id == bot_id,
            BotTool.tool_name == tool_data.tool_name
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Tool already exists on this bot"
        )
    
    tool = BotTool(
        bot_id=bot_id,
        **tool_data.model_dump()
    )
    
    bot.tools_enabled = True
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    
    return BotToolResponse.model_validate(tool)


@router.patch("/{bot_id}/tools/{tool_id}", response_model=BotToolResponse)
async def update_bot_tool(
    bot_id: uuid.UUID,
    tool_id: uuid.UUID,
    tool_data: BotToolUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a bot tool."""
    result = await db.execute(
        select(BotTool).where(
            BotTool.id == tool_id,
            BotTool.bot_id == bot_id
        )
    )
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Update fields
    update_data = tool_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)
    
    await db.commit()
    await db.refresh(tool)
    
    return BotToolResponse.model_validate(tool)


@router.delete("/{bot_id}/tools/{tool_id}", status_code=204)
async def delete_bot_tool(
    bot_id: uuid.UUID,
    tool_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a tool from a bot."""
    result = await db.execute(
        select(BotTool).where(
            BotTool.id == tool_id,
            BotTool.bot_id == bot_id
        )
    )
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    await db.delete(tool)
    await db.commit()


# ─────────────────────────────────────────────────────────────
# Statistics (Admin)
# ─────────────────────────────────────────────────────────────

@router.get("/stats/overview", response_model=BotStatsResponse)
async def get_bot_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_admin)],
):
    """Get bot statistics (admin only)."""
    # Count by status
    status_counts = {}
    for status in ["running", "stopped", "error"]:
        result = await db.execute(
            select(func.count(Bot.id)).where(Bot.status == status)
        )
        status_counts[status] = result.scalar()
    
    # Total bots
    result = await db.execute(select(func.count(Bot.id)))
    total_bots = result.scalar()
    
    # Total messages and tokens
    result = await db.execute(select(func.sum(Bot.total_messages)))
    total_messages = result.scalar() or 0
    
    result = await db.execute(select(func.sum(Bot.total_tokens_used)))
    total_tokens = result.scalar() or 0
    
    return BotStatsResponse(
        total_bots=total_bots,
        running_bots=status_counts.get("running", 0),
        stopped_bots=status_counts.get("stopped", 0),
        error_bots=status_counts.get("error", 0),
        total_messages=total_messages,
        total_tokens=total_tokens,
    )
