"""
Telegram Webhook Endpoint
Receives updates from Telegram bots
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from app.core.database import get_db
from app.models.bot import Bot
from app.models.session import Session
from app.models.message import Message
from app.core.database import get_redis
from app.schemas.bot import MessageCreate, SessionCreate
from app.integrations.telegram.types import TelegramUpdate
from app.integrations.telegram.client import TelegramClient, inline_keyboard, keyboard_button

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


async def get_bot_by_token(db: AsyncSession, token: str) -> Optional[Bot]:
    """Get bot by telegram token"""
    result = await db.execute(
        select(Bot).where(Bot.telegram_token == token, Bot.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_or_create_session(
    db: AsyncSession,
    bot_id: int,
    chat_id: int,
    chat_type: str,
    chat_title: Optional[str] = None,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> Session:
    """Get or create a session for a chat"""
    result = await db.execute(
        select(Session).where(
            Session.bot_id == bot_id,
            Session.external_id == str(chat_id),
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        session = Session(
            bot_id=bot_id,
            external_id=str(chat_id),
            chat_type=chat_type,
            chat_title=chat_title,
            username=username,
            first_name=first_name,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
    else:
        # Update chat info
        session.chat_type = chat_type
        if chat_title:
            session.chat_title = chat_title
        session.username = username
        session.first_name = first_name
        await db.commit()

    return session


async def send_to_message_queue(
    redis_client: redis.Redis,
    bot_id: int,
    session_id: int,
    message_id: int,
    role: str,
    content: str,
    metadata: dict,
):
    """Send message to Redis queue for processing"""
    import json

    payload = json.dumps({
        "bot_id": bot_id,
        "session_id": session_id,
        "message_id": message_id,
        "role": role,
        "content": content,
        "metadata": metadata,
    })

    await redis_client.lpush("bot:messages:queue", payload)
    logger.debug(f"Message queued for bot {bot_id}")


@router.post("/bot/{token}")
async def receive_webhook(
    token: str,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive webhook update from Telegram

    This endpoint is called by Telegram when a bot receives a message.
    The bot_token in the path identifies which bot this update is for.
    """
    # Get bot from database
    bot = await get_bot_by_token(db, token)
    if not bot:
        logger.warning(f"Webhook for unknown/inactive bot token")
        raise HTTPException(status_code=404, detail="Bot not found or inactive")

    # Parse update
    try:
        data = await request.json()
        update = TelegramUpdate(**data)
    except Exception as e:
        logger.error(f"Failed to parse update: {e}")
        raise HTTPException(status_code=400, detail="Invalid update format")

    # Get message
    message = update.effective_message
    if not message:
        return {"ok": True}  # Acknowledge non-message updates

    # Skip messages from other bots
    if message.from_user and message.from_user.is_bot and message.from_user.id != bot.telegram_token:
        return {"ok": True}

    # Get or create session
    session = await get_or_create_session(
        db=db,
        bot_id=bot.id,
        chat_id=message.chat.id,
        chat_type=message.chat.type.value,
        chat_title=message.chat.title,
        username=message.from_user.username if message.from_user else None,
        first_name=message.from_user.first_name if message.from_user else None,
    )

    # Handle commands
    if message.is_command:
        command = message.command
        if command:
            logger.info(f"Command /{command} from chat {message.chat.id}")

            # Store command as message
            msg_record = Message(
                session_id=session.id,
                role="user",
                content=f"/{command} {message.text[len(command)+1:] if message.text and len(message.text) > len(command) else ''}".strip(),
                model=bot.model_name,
                metadata={
                    "command": command,
                    "message_id": message.message_id,
                    "update_type": update.update_type.value if update.update_type else "message",
                }
            )
            db.add(msg_record)
            await db.commit()

            # Queue for processing
            redis_client = await get_redis()
            await send_to_message_queue(
                redis_client,
                bot.id,
                session.id,
                msg_record.id,
                "user",
                msg_record.content,
                {"command": command, "chat_id": message.chat.id, "message_id": message.message_id},
            )
            await redis_client.close()

            return {"ok": True}

    # Store message
    msg_record = Message(
        session_id=session.id,
        role="user",
        content=message.content_text,
        model=bot.model_name,
        metadata={
            "message_id": message.message_id,
            "update_type": update.update_type.value if update.update_type else "message",
        }
    )
    db.add(msg_record)
    await db.commit()

    # Queue for processing
    redis_client = await get_redis()
    await send_to_message_queue(
        redis_client,
        bot.id,
        session.id,
        msg_record.id,
        "user",
        message.content_text,
        {"chat_id": message.chat.id, "message_id": message.message_id},
    )
    await redis_client.close()

    return {"ok": True}


@router.get("/bot/{token}/info")
async def get_webhook_info(token: str):
    """Get webhook info for debugging"""
    bot = TelegramClient(token)
    try:
        info = await bot.get_webhook_info()
        return {
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        }
    finally:
        await bot.close()
