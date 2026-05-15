"""
Telegram API Endpoints
Manage Telegram bot integrations
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bot import Bot
from app.models.user import User
from app.schemas.bot import BotTelegramConfig, WebhookInfoResponse
from app.integrations.telegram.client import TelegramClient
from app.integrations.telegram.webhook import WebhookManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


def get_webhook_manager() -> WebhookManager:
    """Get webhook manager from app state"""
    from app.main import app
    return app.state.webhook_manager


@router.post("/bots/{bot_id}/connect")
async def connect_telegram_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Connect a Telegram bot to a platform bot

    This verifies the bot token and sets up webhook.
    """
    # Get bot
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    # Verify token with Telegram
    client = TelegramClient(bot.telegram_token)
    try:
        bot_info = await client.get_me()
        logger.info(f"Connected Telegram bot: @{bot_info.username}")

        # Get current webhook info
        webhook_info = await client.get_webhook_info()

        return {
            "ok": True,
            "bot": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
            },
            "webhook": {
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count,
            } if webhook_info.url else None,
        }

    except Exception as e:
        logger.error(f"Failed to connect Telegram bot: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid bot token: {str(e)}")
    finally:
        await client.close()


@router.post("/bots/{bot_id}/webhook/set")
async def set_webhook(
    bot_id: int,
    base_url: str,
    max_connections: int = 40,
    allowed_updates: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Set webhook URL for a Telegram bot

    base_url: Your public URL where Telegram can reach this server
    allowed_updates: Comma-separated list of update types (e.g., "message,callback_query")
    """
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    # Set webhook
    success = await webhook_manager.set_webhook(
        bot_token=bot.telegram_token,
        path=f"/api/v1/webhook/bot/{bot.telegram_token}",
        max_connections=max_connections,
        allowed_updates=allowed_updates.split(",") if allowed_updates else None,
    )

    if success:
        return {"ok": True, "url": f"{base_url}/api/v1/webhook/bot/{bot.telegram_token}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to set webhook")


@router.post("/bots/{bot_id}/webhook/delete")
async def delete_webhook(
    bot_id: int,
    drop_pending_updates: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """Delete webhook for a Telegram bot"""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    success = await webhook_manager.delete_webhook(bot.telegram_token)
    return {"ok": success}


@router.get("/bots/{bot_id}/webhook/info", response_model=WebhookInfoResponse)
async def get_webhook_info(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get webhook information for a Telegram bot"""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    client = TelegramClient(bot.telegram_token)
    try:
        info = await client.get_webhook_info()
        return WebhookInfoResponse(
            url=info.url,
            has_custom_certificate=info.has_custom_certificate,
            pending_update_count=info.pending_update_count,
            last_error_message=info.last_error_message,
            max_connections=info.max_connections,
        )
    finally:
        await client.close()


@router.post("/bots/{bot_id}/commands/set")
async def set_bot_commands(
    bot_id: int,
    commands: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set bot command menu

    commands: List of {"command": "start", "description": "Start the bot"}
    """
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    client = TelegramClient(bot.telegram_token)
    try:
        await client.set_my_commands(commands)
        return {"ok": True, "commands": commands}
    finally:
        await client.close()


@router.get("/bots/{bot_id}/info")
async def get_telegram_bot_info(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Telegram bot information"""
    result = await db.execute(
        select(Bot).where(Bot.id == bot_id, Bot.owner_id == current_user.id)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not bot.telegram_token:
        raise HTTPException(status_code=400, detail="Telegram token not configured")

    client = TelegramClient(bot.telegram_token)
    try:
        info = await client.get_me()
        return {
            "id": info.id,
            "is_bot": info.is_bot,
            "username": info.username,
            "first_name": info.first_name,
            "last_name": info.last_name,
            "can_join_groups": info.can_join_groups,
            "can_read_all_group_messages": info.can_read_all_group_messages,
            "supports_inline_queries": info.supports_inline_queries,
        }
    finally:
        await client.close()


@router.post("/test/send-message")
async def test_send_message(
    token: str,
    chat_id: int,
    text: str,
):
    """Test sending a message (for debugging)"""
    client = TelegramClient(token)
    try:
        message = await client.send_message(chat_id=chat_id, text=text)
        return {
            "ok": True,
            "message_id": message.message_id,
            "chat_id": message.chat.id,
        }
    finally:
        await client.close()
