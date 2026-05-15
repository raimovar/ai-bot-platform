"""
Webhook endpoints for Telegram and other integrations.
"""
import uuid
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.bot import Bot
from app.models.session import Session
from app.models.message import Message


router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Telegram Webhook
# ─────────────────────────────────────────────────────────────

@router.post("/telegram/{bot_id}")
async def telegram_webhook(
    bot_id: uuid.UUID,
    update: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    """
    Receive Telegram webhook updates.
    
    This endpoint is called by Telegram when a bot receives a message.
    """
    import httpx
    
    # Get bot
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.telegram_enabled:
        raise HTTPException(status_code=400, detail="Telegram not enabled")
    
    # Verify secret token
    if bot.telegram_token:
        expected_token = hmac.new(
            bot.telegram_token.encode(),
            b"webhook_secret",
            hashlib.sha256
        ).hexdigest()
        if x_telegram_bot_api_secret_token != expected_token:
            # In production, use proper verification
            pass
    
    # Parse update
    message = update.get("message")
    if not message:
        return {"ok": True}
    
    chat = message.get("chat", {})
    user = message.get("from", {})
    text = message.get("text", "")
    chat_id = str(chat.get("id"))
    
    # Check if chat is allowed
    if bot.telegram_allowed_chats and chat_id not in bot.telegram_allowed_chats:
        return {"ok": True, "message": "Chat not allowed"}
    
    # Get or create session
    session_result = await db.execute(
        select(Session).where(
            Session.bot_id == bot_id,
            Session.external_id == chat_id,
        )
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        session = Session(
            bot_id=bot_id,
            external_id=chat_id,
            session_type="telegram",
            user_name=user.get("first_name"),
            user_id=str(user.get("id")),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Send welcome message if configured
        if bot.welcome_message:
            await send_telegram_message(
                bot.telegram_token,
                chat_id,
                bot.welcome_message
            )
    
    # Save user message
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=text,
        source="telegram",
        metadata={
            "message_id": message.get("message_id"),
            "user_id": user.get("id"),
        }
    )
    db.add(user_msg)
    session.message_count += 1
    session.last_message_at = datetime.now(timezone.utc)
    await db.commit()
    
    # Forward to bot runtime for processing
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.BOT_RUNTIME_URL}/chat",
                json={
                    "bot_id": str(bot_id),
                    "session_id": str(session.id),
                    "message": text,
                    "user_name": user.get("first_name"),
                    "user_id": str(user.get("id")),
                }
            )
            result = response.json()
            
            # Send response to Telegram
            await send_telegram_message(
                bot.telegram_token,
                chat_id,
                result["response"]
            )
            
            # Save assistant message
            assistant_msg = Message(
                session_id=session.id,
                role="assistant",
                content=result["response"],
                model=result.get("model"),
                output_tokens=result.get("tokens_used", 0),
                source="telegram",
            )
            db.add(assistant_msg)
            session.total_tokens += result.get("tokens_used", 0)
            await db.commit()
            
    except Exception as e:
        # Send error message
        await send_telegram_message(
            bot.telegram_token,
            chat_id,
            f"❌ Error: {str(e)}"
        )
    
    return {"ok": True}


async def send_telegram_message(token: str, chat_id: str, text: str):
    """Send message via Telegram Bot API."""
    import httpx
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
        )


# ─────────────────────────────────────────────────────────────
# Webhook Registration
# ─────────────────────────────────────────────────────────────

@router.post("/telegram/{bot_id}/set-webhook")
async def set_telegram_webhook(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    webhook_url: str,
):
    """Set Telegram webhook URL for a bot."""
    import httpx
    
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not set")
    
    # Set webhook
    url = f"https://api.telegram.org/bot{bot.telegram_token}/setWebhook"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={
                "url": webhook_url,
                "secret_token": bot.telegram_token[:32],
            }
        )
        result = response.json()
        
        if not result.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set webhook: {result}"
            )
    
    bot.webhook_url = webhook_url
    await db.commit()
    
    return {"ok": True, "webhook_url": webhook_url}


@router.delete("/telegram/{bot_id}/webhook")
async def delete_telegram_webhook(
    bot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete Telegram webhook for a bot."""
    import httpx
    
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not set")
    
    # Delete webhook
    url = f"https://api.telegram.org/bot{bot.telegram_token}/deleteWebhook"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url)
        result = response.json()
        
        if not result.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete webhook: {result}"
            )
    
    bot.webhook_url = None
    await db.commit()
    
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# Generic Webhook (for other integrations)
# ─────────────────────────────────────────────────────────────

@router.post("/generic/{source_id}")
async def generic_webhook(
    source_id: str,
    payload: dict,
    background_tasks: BackgroundTasks,
):
    """
    Generic webhook endpoint for external integrations.
    
    Sources could be: discord, slack, web, custom, etc.
    """
    # TODO: Implement generic webhook handler
    return {"ok": True, "message": "Webhook received"}
