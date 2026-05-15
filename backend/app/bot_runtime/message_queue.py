"""
Message Queue
Redis-based message queue for bot communication
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class MessageQueue:
    """
    Redis-based message queue for bot messages

    Handles message routing, concurrency control, and timeout management.

    Usage:
        queue = MessageQueue(redis_url="redis://localhost:6379/0")
        await queue.connect()

        # Get next message (blocks until available)
        message = await queue.get_message()

        # Acknowledge message
        await queue.ack_message(message_id)

        # Put message back (on failure)
        await queue.nack_message(message_id)
    """

    QUEUE_KEY = "bot:messages:queue"
    PROCESSING_KEY = "bot:messages:processing"
    DLQ_KEY = "bot:messages:dlq"  # Dead letter queue

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_concurrent: int = 10,
        timeout: int = 120,
    ):
        self.redis_url = redis_url
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._processing_count = 0

    async def connect(self):
        """Connect to Redis"""
        if self._connected:
            return

        self._client = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Test connection
        await self._client.ping()

        self._connected = True
        logger.info("Message queue connected to Redis")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Message queue disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self._client is not None

    # =======================
    # Queue Operations
    # =======================

    async def put_message(self, message: Dict[str, Any]) -> bool:
        """
        Add a message to the queue

        Args:
            message: Message dict with bot_id, session_id, content, etc.

        Returns:
            True if added successfully
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Redis")

        try:
            # Add timestamp and generate message_id if not present
            message["queued_at"] = asyncio.get_event_loop().time()
            if "message_id" not in message:
                message["message_id"] = f"{message.get('bot_id')}:{message['queued_at']}"

            # Push to queue
            await self._client.lpush(self.QUEUE_KEY, json.dumps(message))

            logger.debug(f"Message queued: {message.get('message_id')}")
            return True

        except Exception as e:
            logger.exception(f"Failed to queue message: {e}")
            return False

    async def get_message(self, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get next message from queue (blocking)

        Args:
            timeout: Blocking timeout in seconds (default: 1)

        Returns:
            Message dict or None if timeout
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Redis")

        timeout = timeout or 1

        try:
            # Check concurrency limit
            if self._processing_count >= self.max_concurrent:
                await asyncio.sleep(0.1)
                return None

            # Blocking pop from queue
            result = await self._client.brpop(
                self.QUEUE_KEY,
                timeout=timeout,
            )

            if not result:
                return None

            _, message_json = result
            message = json.loads(message_json)

            # Move to processing set
            message_id = message.get("message_id")
            await self._client.zadd(
                self.PROCESSING_KEY,
                {message_id: asyncio.get_event_loop().time()},
            )

            self._processing_count += 1
            logger.debug(f"Message dequeued: {message_id}")

            return message

        except Exception as e:
            logger.exception(f"Failed to get message: {e}")
            return None

    async def ack_message(self, message_id: str):
        """
        Acknowledge message processed successfully

        Args:
            message_id: Message ID
        """
        if not self.is_connected:
            return

        try:
            # Remove from processing set
            await self._client.zrem(self.PROCESSING_KEY, message_id)
            self._processing_count = max(0, self._processing_count - 1)
            logger.debug(f"Message acknowledged: {message_id}")

        except Exception as e:
            logger.exception(f"Failed to ack message: {e}")

    async def nack_message(self, message_id: str, error: Optional[str] = None):
        """
        Mark message as failed, move to DLQ or retry

        Args:
            message_id: Message ID
            error: Optional error message
        """
        if not self.is_connected:
            return

        try:
            # Remove from processing
            await self._client.zrem(self.PROCESSING_KEY, message_id)
            self._processing_count = max(0, self._processing_count - 1)

            # Get retry count
            retry_count = await self._client.hget(f"message:{message_id}:retries", "count") or 0

            if retry_count < 3:
                # Requeue for retry
                await self._client.hincrby(f"message:{message_id}:retries", "count", 1)
                await self._client.lpush(self.QUEUE_KEY, json.dumps({"retry": message_id, "error": error}))
                logger.debug(f"Message requeued for retry: {message_id}")
            else:
                # Move to DLQ
                await self._client.zadd(
                    self.DLQ_KEY,
                    {json.dumps({"message_id": message_id, "error": error}): asyncio.get_event_loop().time()}
                )
                logger.warning(f"Message moved to DLQ: {message_id}")

        except Exception as e:
            logger.exception(f"Failed to nack message: {e}")

    async def get_queue_length(self) -> int:
        """Get current queue length"""
        if not self.is_connected:
            return 0

        try:
            return await self._client.llen(self.QUEUE_KEY)
        except Exception:
            return 0

    async def get_processing_count(self) -> int:
        """Get number of messages currently processing"""
        if not self.is_connected:
            return 0

        try:
            return await self._client.zcard(self.PROCESSING_KEY)
        except Exception:
            return 0

    async def get_dlq_length(self) -> int:
        """Get dead letter queue length"""
        if not self.is_connected:
            return 0

        try:
            return await self._client.zcard(self.DLQ_KEY)
        except Exception:
            return 0

    # =======================
    # Cleanup
    # =======================

    async def cleanup_stale_messages(self, max_age_seconds: int = 3600):
        """
        Move stale messages from processing back to queue

        Args:
            max_age_seconds: Max age before considered stale
        """
        if not self.is_connected:
            return

        try:
            now = asyncio.get_event_loop().time()
            cutoff = now - max_age_seconds

            # Get stale messages
            stale = await self._client.zrangebyscore(
                self.PROCESSING_KEY,
                "-inf",
                cutoff,
            )

            for message_id in stale:
                # Remove from processing
                await self._client.zrem(self.PROCESSING_KEY, message_id)
                self._processing_count = max(0, self._processing_count - 1)

                # Requeue
                await self._client.lpush(self.QUEUE_KEY, json.dumps({"stale_retry": message_id}))

            if stale:
                logger.info(f"Cleaned up {len(stale)} stale messages")

        except Exception as e:
            logger.exception(f"Failed to cleanup stale messages: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "queue_length": await self.get_queue_length(),
            "processing_count": await self.get_processing_count(),
            "dlq_length": await self.get_dlq_length(),
            "max_concurrent": self.max_concurrent,
            "connected": self.is_connected,
        }
