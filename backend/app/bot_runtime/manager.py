"""
Bot Runtime Manager
Manages all bot instances and their lifecycles
"""

import asyncio
import logging
import signal
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .bot_instance import BotInstance
from .message_queue import MessageQueue
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class BotStatus(str, Enum):
    """Bot runtime status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BotRuntimeConfig:
    """Configuration for bot runtime"""
    redis_url: str = "redis://localhost:6379/0"
    db_url: str = "postgresql+asyncpg://aibot:aibot_password@localhost:5432/aibot_platform"
    api_base_url: str = "http://localhost:8000"
    max_concurrent_messages: int = 10
    message_timeout: int = 120
    cleanup_interval: int = 300


@dataclass
class BotStats:
    """Runtime statistics for a bot"""
    messages_processed: int = 0
    messages_failed: int = 0
    avg_response_time: float = 0.0
    last_message_at: Optional[datetime] = None
    last_error: Optional[str] = None


class BotRuntimeManager:
    """
    Central manager for all bot runtime instances

    Manages lifecycle, scaling, and message routing for all bots.

    Usage:
        manager = BotRuntimeManager(config)
        await manager.start()

        # Add a bot
        await manager.add_bot(bot_id, bot_config)

        # Remove a bot
        await manager.remove_bot(bot_id)

        # Get status
        status = manager.get_status()

        # Stop all
        await manager.stop_all()
    """

    def __init__(self, config: Optional[BotRuntimeConfig] = None):
        self.config = config or BotRuntimeConfig()
        self._bots: Dict[int, BotInstance] = {}
        self._status: Dict[int, BotStatus] = {}
        self._stats: Dict[int, BotStats] = {}

        self._message_queue: Optional[MessageQueue] = None
        self._session_manager: Optional[SessionManager] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None

        # Event hooks
        self._on_bot_start: List[Callable] = []
        self._on_bot_stop: List[Callable] = []
        self._on_bot_error: List[Callable] = []

    # =======================
    # Lifecycle
    # =======================

    async def start(self):
        """Start the runtime manager"""
        if self._running:
            logger.warning("Runtime manager already running")
            return

        logger.info("Starting Bot Runtime Manager...")

        # Initialize components
        self._message_queue = MessageQueue(
            redis_url=self.config.redis_url,
            max_concurrent=self.config.max_concurrent_messages,
            timeout=self.config.message_timeout,
        )

        self._session_manager = SessionManager(
            db_url=self.config.db_url,
            redis_url=self.config.redis_url,
        )

        await self._message_queue.connect()
        await self._session_manager.connect()

        self._running = True
        self._start_time = datetime.utcnow()

        # Start message processing loop
        self._task = asyncio.create_task(self._process_loop())

        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())

        logger.info("Bot Runtime Manager started")

    async def stop(self):
        """Stop the runtime manager"""
        if not self._running:
            return

        logger.info("Stopping Bot Runtime Manager...")

        self._running = False

        # Stop all bots
        await self.stop_all()

        # Stop components
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._message_queue:
            await self._message_queue.disconnect()

        if self._session_manager:
            await self._session_manager.disconnect()

        logger.info("Bot Runtime Manager stopped")

    # =======================
    # Bot Management
    # =======================

    async def add_bot(
        self,
        bot_id: int,
        config: dict,
        system_prompt: str,
        model_config: dict,
    ) -> bool:
        """
        Add and start a bot

        Args:
            bot_id: Bot ID in database
            config: Bot configuration (token, settings, etc.)
            system_prompt: System prompt for the bot
            model_config: Model configuration (provider, model, etc.)

        Returns:
            True if bot started successfully
        """
        if bot_id in self._bots:
            logger.warning(f"Bot {bot_id} already running")
            return True

        try:
            self._status[bot_id] = BotStatus.STARTING
            self._stats[bot_id] = BotStats()

            # Create bot instance
            bot = BotInstance(
                bot_id=bot_id,
                config=config,
                system_prompt=system_prompt,
                model_config=model_config,
                message_queue=self._message_queue,
                session_manager=self._session_manager,
            )

            # Start the bot
            await bot.start()

            self._bots[bot_id] = bot
            self._status[bot_id] = BotStatus.RUNNING

            logger.info(f"Bot {bot_id} started")
            await self._notify_bot_start(bot_id)

            return True

        except Exception as e:
            logger.exception(f"Failed to start bot {bot_id}: {e}")
            self._status[bot_id] = BotStatus.ERROR
            self._stats[bot_id] = BotStats(last_error=str(e))
            await self._notify_bot_error(bot_id, e)
            return False

    async def remove_bot(self, bot_id: int):
        """Remove and stop a bot"""
        if bot_id not in self._bots:
            return

        logger.info(f"Stopping bot {bot_id}...")

        try:
            self._status[bot_id] = BotStatus.STOPPING
            await self._bots[bot_id].stop()
            del self._bots[bot_id]
            self._status[bot_id] = BotStatus.STOPPED
            self._stats.pop(bot_id, None)

            logger.info(f"Bot {bot_id} stopped")
            await self._notify_bot_stop(bot_id)

        except Exception as e:
            logger.exception(f"Error stopping bot {bot_id}: {e}")
            self._status[bot_id] = BotStatus.ERROR

    async def restart_bot(self, bot_id: int):
        """Restart a bot"""
        if bot_id not in self._bots:
            logger.warning(f"Bot {bot_id} not found")
            return

        logger.info(f"Restarting bot {bot_id}...")
        bot = self._bots[bot_id]

        await bot.stop()
        await bot.start()

        self._status[bot_id] = BotStatus.RUNNING
        logger.info(f"Bot {bot_id} restarted")

    async def stop_all(self):
        """Stop all running bots"""
        bot_ids = list(self._bots.keys())
        for bot_id in bot_ids:
            await self.remove_bot(bot_id)

    # =======================
    # Message Processing
    # =======================

    async def _process_loop(self):
        """Main message processing loop"""
        while self._running:
            try:
                # Get message from queue
                message = await self._message_queue.get_message()

                if message:
                    await self._process_message(message)
                else:
                    # No messages, sleep briefly
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in process loop: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: dict):
        """Process a single message"""
        bot_id = message.get("bot_id")
        if bot_id not in self._bots:
            logger.warning(f"Message for unknown bot {bot_id}")
            return

        bot = self._bots[bot_id]
        start_time = asyncio.get_event_loop().time()

        try:
            await bot.process_message(message)
            self._stats[bot_id].messages_processed += 1

            # Update response time
            elapsed = asyncio.get_event_loop().time() - start_time
            stats = self._stats[bot_id]
            stats.avg_response_time = (
                (stats.avg_response_time * (stats.messages_processed - 1) + elapsed)
                / stats.messages_processed
            )
            stats.last_message_at = datetime.utcnow()

        except Exception as e:
            logger.exception(f"Error processing message for bot {bot_id}: {e}")
            self._stats[bot_id].messages_failed += 1
            self._stats[bot_id].last_error = str(e)

    # =======================
    # Cleanup
    # =======================

    async def _cleanup_loop(self):
        """Periodic cleanup of stale sessions"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._session_manager.cleanup_stale_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")

    # =======================
    # Status & Monitoring
    # =======================

    def get_status(self) -> dict:
        """Get overall runtime status"""
        running = sum(1 for s in self._status.values() if s == BotStatus.RUNNING)
        errors = sum(1 for s in self._status.values() if s == BotStatus.ERROR)

        return {
            "running": self._running,
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0,
            "total_bots": len(self._bots),
            "running_bots": running,
            "error_bots": errors,
            "bots": {
                bot_id: {
                    "status": status.value,
                    "stats": {
                        "messages_processed": stats.messages_processed,
                        "messages_failed": stats.messages_failed,
                        "avg_response_time": stats.avg_response_time,
                        "last_message_at": stats.last_message_at.isoformat() if stats.last_message_at else None,
                        "last_error": stats.last_error,
                    }
                }
                for bot_id, status in self._status.items()
                for stats in [self._stats.get(bot_id, BotStats())]
            }
        }

    def get_bot_status(self, bot_id: int) -> Optional[dict]:
        """Get status for a specific bot"""
        if bot_id not in self._bots:
            return None

        status = self._status.get(bot_id, BotStatus.STOPPED)
        stats = self._stats.get(bot_id, BotStats())

        return {
            "status": status.value,
            "stats": {
                "messages_processed": stats.messages_processed,
                "messages_failed": stats.messages_failed,
                "avg_response_time": stats.avg_response_time,
                "last_message_at": stats.last_message_at.isoformat() if stats.last_message_at else None,
                "last_error": stats.last_error,
            }
        }

    # =======================
    # Event Hooks
    # =======================

    def on_bot_start(self, callback: Callable):
        """Register callback for bot start events"""
        self._on_bot_start.append(callback)

    def on_bot_stop(self, callback: Callable):
        """Register callback for bot stop events"""
        self._on_bot_stop.append(callback)

    def on_bot_error(self, callback: Callable):
        """Register callback for bot error events"""
        self._on_bot_error.append(callback)

    async def _notify_bot_start(self, bot_id: int):
        """Notify listeners of bot start"""
        for callback in self._on_bot_start:
            try:
                await callback(bot_id)
            except Exception as e:
                logger.exception(f"Error in on_bot_start callback: {e}")

    async def _notify_bot_stop(self, bot_id: int):
        """Notify listeners of bot stop"""
        for callback in self._on_bot_stop:
            try:
                await callback(bot_id)
            except Exception as e:
                logger.exception(f"Error in on_bot_stop callback: {e}")

    async def _notify_bot_error(self, bot_id: int, error: Exception):
        """Notify listeners of bot error"""
        for callback in self._on_bot_error:
            try:
                await callback(bot_id, error)
            except Exception as e:
                logger.exception(f"Error in on_bot_error callback: {e}")


# =======================
# Global Instance
# =======================

_manager: Optional[BotRuntimeManager] = None


async def get_runtime_manager() -> BotRuntimeManager:
    """Get or create global runtime manager"""
    global _manager
    if _manager is None:
        _manager = BotRuntimeManager()
        await _manager.start()
    return _manager


async def shutdown_runtime_manager():
    """Shutdown global runtime manager"""
    global _manager
    if _manager:
        await _manager.stop()
        _manager = None
