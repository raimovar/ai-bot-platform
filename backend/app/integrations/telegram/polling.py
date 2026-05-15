"""
Telegram Polling Consumer
Long-polling fallback when webhooks aren't available
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable, List
from dataclasses import dataclass
from datetime import datetime

from .client import TelegramClient
from .types import TelegramUpdate

logger = logging.getLogger(__name__)


@dataclass
class PollingConfig:
    """Configuration for polling consumer"""
    timeout: int = 55  # Long polling timeout ( Telegram max is 50 )
    limit: int = 100   # Max updates per request
    allowed_updates: Optional[List[str]] = None  # None = all updates
    retry_delay: float = 1.0   # Initial retry delay
    max_retry_delay: float = 60.0  # Max retry delay
    retry_multiplier: float = 2.0  # Exponential backoff multiplier


class PollingConsumer:
    """
    Long-polling consumer for Telegram updates

    This is a fallback when webhooks can't be used.
    Provides automatic reconnection and rate limiting.

    Usage:
        async def handler(update: TelegramUpdate):
            await process_update(update)

        consumer = PollingConsumer(bot_token, handler)
        await consumer.start()

        # Later:
        await consumer.stop()
    """

    def __init__(
        self,
        bot_token: str,
        handler: Callable[[TelegramUpdate], Awaitable[None]],
        config: Optional[PollingConfig] = None,
        offset: int = 0,
    ):
        self.bot_token = bot_token
        self.handler = handler
        self.config = config or PollingConfig()
        self.offset = offset

        self._client: Optional[TelegramClient] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._retry_delay = self.config.retry_delay

        # Statistics
        self.updates_received = 0
        self.updates_processed = 0
        self.errors = 0
        self.started_at: Optional[datetime] = None

    async def start(self):
        """Start polling for updates"""
        if self._running:
            logger.warning("Consumer already running")
            return

        self._running = True
        self._client = TelegramClient(self.bot_token)
        self.started_at = datetime.utcnow()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Polling started for bot {self.bot_token[:8]}...")

    async def stop(self):
        """Stop polling"""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.close()

        logger.info(
            f"Polling stopped. Stats: received={self.updates_received}, "
            f"processed={self.updates_processed}, errors={self.errors}"
        )

    async def _poll_loop(self):
        """Main polling loop with automatic reconnection"""
        while self._running:
            try:
                await self._fetch_updates()
                # Reset retry delay on success
                self._retry_delay = self.config.retry_delay

            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break

            except Exception as e:
                self.errors += 1
                logger.exception(f"Polling error: {e}")

                # Exponential backoff
                await asyncio.sleep(self._retry_delay)
                self._retry_delay = min(
                    self._retry_delay * self.config.retry_multiplier,
                    self.config.max_retry_delay,
                )

    async def _fetch_updates(self):
        """Fetch and process updates"""
        if not self._client:
            return

        # Use getUpdates API
        params = {
            "timeout": self.config.timeout,
            "limit": self.config.limit,
            "offset": self.offset,
        }

        if self.config.allowed_updates:
            params["allowed_updates"] = self.config.allowed_updates

        response = await self._client._request("getUpdates", params)
        result = response.get("result", [])

        if not result:
            return

        self.updates_received += len(result)

        for update_data in result:
            try:
                update = TelegramUpdate(**update_data)

                # Update offset for next request
                self.offset = update.update_id + 1

                # Process update
                await self._process_update(update)

            except Exception as e:
                logger.exception(f"Error processing update: {e}")
                self.errors += 1

    async def _process_update(self, update: TelegramUpdate):
        """Process a single update"""
        try:
            await self.handler(update)
            self.updates_processed += 1

            update_type = update.update_type
            logger.debug(f"Processed {update_type} update {update.update_id}")

        except Exception as e:
            logger.exception(f"Handler error for update {update.update_id}: {e}")
            self.errors += 1

    async def reset_offset(self):
        """Reset offset to get all pending updates"""
        self.offset = 0
        logger.info("Offset reset to 0")

    def get_stats(self) -> dict:
        """Get polling statistics"""
        uptime = None
        if self.started_at:
            uptime = (datetime.utcnow() - self.started_at).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "updates_received": self.updates_received,
            "updates_processed": self.updates_processed,
            "errors": self.errors,
            "current_offset": self.offset,
            "retry_delay": self._retry_delay,
        }


class PollingManager:
    """
    Manager for multiple polling consumers

    Usage:
        manager = PollingManager()

        # Add a bot
        await manager.add_bot(bot_token, handler)

        # Add multiple bots
        await manager.add_bot(bot_token2, handler2)

        # Start all
        await manager.start_all()

        # Later: stop all
        await manager.stop_all()
    """

    def __init__(self):
        self._consumers: dict[str, PollingConsumer] = {}
        self._handlers: dict[str, Callable[[TelegramUpdate], Awaitable[None]]] = {}

    async def add_bot(
        self,
        bot_token: str,
        handler: Callable[[TelegramUpdate], Awaitable[None]],
        config: Optional[PollingConfig] = None,
    ):
        """
        Add a bot to poll

        Args:
            bot_token: Telegram bot token
            handler: Handler function for updates
            config: Optional polling configuration
        """
        if bot_token in self._consumers:
            logger.warning(f"Bot {bot_token[:8]}... already added")
            return

        consumer = PollingConsumer(bot_token, handler, config)
        self._consumers[bot_token] = consumer
        self._handlers[bot_token] = handler
        logger.info(f"Added bot {bot_token[:8]}... to polling manager")

    async def remove_bot(self, bot_token: str):
        """Remove a bot from polling"""
        if bot_token in self._consumers:
            await self._consumers[bot_token].stop()
            del self._consumers[bot_token]
            self._handlers.pop(bot_token, None)
            logger.info(f"Removed bot {bot_token[:8]}... from polling")

    async def start_all(self):
        """Start all polling consumers"""
        for bot_token, consumer in self._consumers.items():
            if not consumer._running:
                await consumer.start()

    async def stop_all(self):
        """Stop all polling consumers"""
        for bot_token, consumer in self._consumers.items():
            if consumer._running:
                await consumer.stop()

    async def restart_bot(self, bot_token: str):
        """Restart polling for a specific bot"""
        if bot_token in self._consumers:
            await self._consumers[bot_token].stop()
            self._consumers[bot_token] = PollingConsumer(
                bot_token,
                self._handlers[bot_token],
            )
            await self._consumers[bot_token].start()

    def get_stats(self) -> dict:
        """Get statistics for all bots"""
        return {
            bot_token: consumer.get_stats()
            for bot_token, consumer in self._consumers.items()
        }

    @property
    def active_count(self) -> int:
        """Number of active polling consumers"""
        return sum(1 for c in self._consumers.values() if c._running)

    @property
    def bot_count(self) -> int:
        """Total number of bots"""
        return len(self._consumers)
