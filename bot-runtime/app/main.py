"""
Bot Runtime Engine - Main Entry Point

This service handles:
- Bot lifecycle management
- Message processing
- LLM calls
- Memory management
- Tool execution
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.engine.bot_instance import BotInstance
from app.engine.manager import BotManager
from app.engine.message_queue import MessageQueue
from app.llm.factory import LLMFactory
from app.memory.manager import MemoryManager


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    bot_id: str
    session_id: str
    message: str
    user_name: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    tokens_used: int


class BotStatusResponse(BaseModel):
    bot_id: str
    status: str
    is_running: bool


# ─────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Bot Runtime Engine",
    version="1.0.0",
    description="AI Bot execution engine",
)

# Global instances
bot_manager: Optional[BotManager] = None
message_queue: Optional[MessageQueue] = None


@app.on_event("startup")
async def startup():
    """Initialize runtime components."""
    global bot_manager, message_queue
    
    # Initialize Redis
    redis_client = redis.from_url(settings.REDIS_URL)
    
    # Initialize message queue
    message_queue = MessageQueue(redis_client)
    
    # Initialize bot manager
    bot_manager = BotManager(
        db_url=settings.DATABASE_URL,
        redis_client=redis_client,
        ai_gateway_url=settings.AI_GATEWAY_URL,
    )
    
    print("✅ Bot Runtime Engine started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if bot_manager:
        await bot_manager.stop_all()
    print("👋 Bot Runtime Engine stopped")


# ─────────────────────────────────────────────────────────────
# Chat Endpoint
# ─────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message through a bot.
    
    This is the main entry point for all bot messages.
    """
    import time
    start_time = time.time()
    
    bot_id = uuid.UUID(request.bot_id)
    session_id = uuid.UUID(request.session_id)
    
    # Get or create bot instance
    bot_instance = await bot_manager.get_bot(bot_id)
    
    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot not found or not running")
    
    # Process message
    try:
        response = await bot_instance.process_message(
            message=request.message,
            session_id=session_id,
            user_name=request.user_name,
            user_id=request.user_id,
        )
        
        tokens_used = response.get("tokens_used", 0)
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            response=response["content"],
            model=response.get("model", "unknown"),
            tokens_used=tokens_used,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Bot Lifecycle Endpoints
# ─────────────────────────────────────────────────────────────

@app.post("/bots/{bot_id}/start")
async def start_bot(bot_id: uuid.UUID, background_tasks: BackgroundTasks):
    """Start a bot."""
    if bot_manager.is_running(bot_id):
        return {"status": "already_running"}
    
    try:
        await bot_manager.start_bot(bot_id)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bots/{bot_id}/stop")
async def stop_bot(bot_id: uuid.UUID):
    """Stop a bot."""
    if not bot_manager.is_running(bot_id):
        return {"status": "already_stopped"}
    
    await bot_manager.stop_bot(bot_id)
    return {"status": "stopped"}


@app.get("/bots/{bot_id}/status", response_model=BotStatusResponse)
async def get_bot_status(bot_id: uuid.UUID):
    """Get bot status."""
    is_running = bot_manager.is_running(bot_id)
    
    return BotStatusResponse(
        bot_id=str(bot_id),
        status="running" if is_running else "stopped",
        is_running=is_running,
    )


@app.get("/bots/status")
async def get_all_status():
    """Get status of all bots."""
    return {
        "running_bots": [str(bid) for bid in bot_manager.running_bots.keys()],
        "total": len(bot_manager.running_bots),
    }


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
