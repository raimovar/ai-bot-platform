"""
Telegram Webhook Handler
FastAPI endpoints for receiving Telegram updates via webhook
"""

import logging
from typing import Optional, Callable, Awaitable, Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from pydantic import BaseModel

from .types import TelegramUpdate, UpdateType
from .client import TelegramClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["telegram"])


class WebhookUpdate(BaseModel):
    """Webhook update from Telegram"""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None


# Global webhook handlers registry
_webhook_handlers: Dict[str, Callable[[TelegramUpdate], Awaitable[None]]] = {}
_webhook_verification_tokens: Dict[str, str] = {}


async def default_update_handler(update: TelegramUpdate):
    """Default handler - just log updates"""
    update_type = update.update_type
    logger.debug(f"Received {update_type} update: {update.update_id}")


async def register_webhook_handler(
    bot_token: str,
    handler: Callable[[TelegramUpdate], Awaitable[None]],
    secret_token: Optional[str] = None,
):
    """
    Register a handler for a bot's webhook updates

    Args:
        bot_token: Telegram bot token
        handler: Async function to handle updates
        secret_token: Optional secret for verification
    """
    _webhook_handlers[bot_token] = handler
    if secret_token:
        _webhook_handlers[f"{bot_token}:secret"] = secret_token


async def unregister_webhook_handler(bot_token: str):
    """Unregister webhook handler for a bot"""
    _webhook_handlers.pop(bot_token, None)
    _webhook_handlers.pop(f"{bot_token}:secret", None)


def verify_secret_token(
    bot_token: str,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
) -> bool:
    """
    Verify secret token if configured

    Raises:
        HTTPException: If token doesn't match
    """
    expected_secret = _webhook_handlers.get(f"{bot_token}:secret")
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


async def process_update(bot_token: str, update: TelegramUpdate):
    """Process an incoming update"""
    handler = _webhook_handlers.get(bot_token, default_update_handler)

    try:
        await handler(update)
    except Exception as e:
        logger.exception(f"Error processing update {update.update_id}: {e}")


@router.post("/bot/{bot_token}")
async def receive_update(
    bot_token: str,
    update: WebhookUpdate,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    """
    Receive webhook update from Telegram

    This endpoint is called by Telegram when a bot receives a message.
    The bot_token in the path identifies which bot this update is for.
    """
    # Verify secret token if configured
    expected_secret = _webhook_handlers.get(f"{bot_token}:secret")
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        logger.warning(f"Invalid secret token for bot {bot_token[:8]}...")
        raise HTTPException(status_code=403, detail="Forbidden")

    # Convert to TelegramUpdate model
    try:
        tg_update = TelegramUpdate(**update.model_dump(exclude_none=True))
    except Exception as e:
        logger.warning(f"Invalid update format: {e}")
        raise HTTPException(status_code=400, detail="Invalid update format")

    # Process in background
    # Note: In production, this should go to a task queue
    try:
        await process_update(bot_token, tg_update)
    except Exception as e:
        logger.exception(f"Error processing update: {e}")

    return {"ok": True}


@router.get("/bot/{bot_token}/info")
async def get_webhook_info(
    bot_token: str,
    verify: bool = Depends(lambda: True),
):
    """
    Get webhook info for a bot

    Note: This requires the bot token to call getWebhookInfo
    """
    client = TelegramClient(bot_token)
    try:
        info = await client.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
        }
    finally:
        await client.close()


@router.post("/bot/{bot_token}/set")
async def set_webhook(
    bot_token: str,
    url: str,
    max_connections: int = 40,
    allowed_updates: Optional[str] = None,
):
    """
    Set webhook URL for a bot

    The URL should point to this server's /webhook/bot/{token} endpoint.
    """
    client = TelegramClient(bot_token)

    try:
        # Verify URL is accessible
        webhook_url = f"{url.rstrip('/')}/webhook/bot/{bot_token}"

        result = await client.set_webhook(
            url=webhook_url,
            max_connections=max_connections,
            allowed_updates=allowed_updates.split(",") if allowed_updates else None,
        )

        if result:
            logger.info(f"Webhook set for bot {bot_token[:8]}...: {webhook_url}")
            return {"ok": True, "url": webhook_url}
        else:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
    finally:
        await client.close()


@router.post("/bot/{bot_token}/delete")
async def delete_webhook(
    bot_token: str,
    drop_pending_updates: bool = False,
):
    """Delete webhook for a bot"""
    client = TelegramClient(bot_token)

    try:
        result = await client.delete_webhook(drop_pending_updates)
        return {"ok": result}
    finally:
        await client.close()


class WebhookManager:
    """
    Manager for webhook operations

    Usage:
        manager = WebhookManager("https://your-domain.com")

        # Set webhook for a bot
        await manager.set_webhook(bot_token, "/api/webhook/handler")

        # Register handler
        async def handler(update: TelegramUpdate):
            ...

        await manager.register_handler(bot_token, handler, secret="my-secret")
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._handlers: Dict[str, Callable[[TelegramUpdate], Awaitable[None]]] = {}

    @property
    def webhook_url(self) -> str:
        """Get the webhook base URL"""
        return f"{self.base_url}/webhook"

    async def set_webhook(
        self,
        bot_token: str,
        path: str = "/webhook/bot/{token}",
        max_connections: int = 40,
        allowed_updates: Optional[list] = None,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Set webhook URL for a bot

        Args:
            bot_token: Telegram bot token
            path: Webhook path (default: /webhook/bot/{token})
            max_connections: Max connections
            allowed_updates: Update types to receive
            secret: Secret token for verification

        Returns:
            True if successful
        """
        url = path.format(token=bot_token)
        full_url = f"{self.base_url}{url}"

        client = TelegramClient(bot_token)

        try:
            result = await client.set_webhook(
                url=full_url,
                max_connections=max_connections,
                allowed_updates=allowed_updates,
                secret_token=secret,
            )

            if result:
                logger.info(f"Webhook set: {full_url}")
                if secret:
                    self._handlers[f"{bot_token}:secret"] = secret

            return result
        finally:
            await client.close()

    async def delete_webhook(self, bot_token: str) -> bool:
        """Delete webhook for a bot"""
        client = TelegramClient(bot_token)

        try:
            return await client.delete_webhook()
        finally:
            await client.close()

    async def register_handler(
        self,
        bot_token: str,
        handler: Callable[[TelegramUpdate], Awaitable[None]],
    ):
        """Register a handler for bot updates"""
        self._handlers[bot_token] = handler
        _webhook_handlers[bot_token] = handler

    def unregister_handler(self, bot_token: str):
        """Unregister handler"""
        self._handlers.pop(bot_token, None)
        _webhook_handlers.pop(bot_token, None)
