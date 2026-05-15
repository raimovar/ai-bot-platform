"""
Message Queue - Redis-based queue for bot messages.
"""
import json
import uuid
from typing import Optional
import redis.asyncio as redis


class MessageQueue:
    """
    Redis-based message queue for async bot processing.
    
    Uses Redis lists for queue and pub/sub for notifications.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_name = "bot:messages:queue"
        self.pubsub_channel = "bot:messages:events"
    
    async def enqueue(self, message: dict) -> str:
        """
        Add a message to the queue.
        
        Args:
            message: Message dict with keys:
                - bot_id: UUID
                - session_id: UUID
                - message: str
                - user_name: Optional[str]
                - user_id: Optional[str]
        
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        queue_item = {
            "id": message_id,
            **message,
            "enqueued_at": str(uuid.uuid4()),  # Timestamp
        }
        
        await self.redis.rpush(
            self.queue_name,
            json.dumps(queue_item)
        )
        
        # Notify workers
        await self.redis.publish(
            self.pubsub_channel,
            message_id
        )
        
        return message_id
    
    async def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """
        Get a message from the queue.
        
        Args:
            timeout: Seconds to wait (0 = blocking)
        
        Returns:
            Message dict or None
        """
        result = await self.redis.blpop(self.queue_name, timeout=timeout)
        
        if result:
            _, message_json = result
            return json.loads(message_json)
        
        return None
    
    async def length(self) -> int:
        """Get queue length."""
        return await self.redis.llen(self.queue_name)
    
    async def clear(self):
        """Clear the queue."""
        await self.redis.delete(self.queue_name)
    
    async def subscribe(self):
        """Subscribe to message events (for workers)."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.pubsub_channel)
        return pubsub
