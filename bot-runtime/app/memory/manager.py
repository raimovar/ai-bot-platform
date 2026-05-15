"""
Memory Manager - Handles short-term and long-term memory.
"""
import json
import uuid
from typing import Optional
import redis.asyncio as redis


class MemoryManager:
    """
    Manages bot memory using Redis.
    
    Types:
    - short_term: Rolling window of recent messages
    - long_term: Vector store with retrieval (future)
    - hybrid: Both combined
    """
    
    def __init__(
        self,
        redis: redis.Redis,
        bot_id: str,
        memory_type: str = "short_term",
        memory_config: dict = None,
    ):
        self.redis = redis
        self.bot_id = bot_id
        self.memory_type = memory_type
        self.config = memory_config or {}
        
        # Config
        self.window_size = self.config.get("window_size", 10)
        
        # Redis keys
        self.history_key = f"bot:{bot_id}:history"
        self.sessions_key = f"bot:{bot_id}:sessions"
    
    def _session_key(self, session_id: uuid.UUID) -> str:
        """Get Redis key for session history."""
        return f"{self.history_key}:{session_id}"
    
    async def add_message(
        self,
        role: str,
        content: str,
        session_id: uuid.UUID,
    ):
        """Add a message to session history."""
        key = self._session_key(session_id)
        
        message = json.dumps({
            "role": role,
            "content": content,
        })
        
        await self.redis.rpush(key, message)
        
        # Trim to window size
        await self.redis.ltrim(key, -self.window_size * 2, -1)
        
        # Set expiry (7 days)
        await self.redis.expire(key, 7 * 24 * 3600)
    
    async def get_history(
        self,
        session_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Get conversation history for a session."""
        key = self._session_key(session_id)
        
        limit = limit or self.window_size
        
        # Get last N messages
        messages = await self.redis.lrange(key, -limit * 2, -1)
        
        return [json.loads(m) for m in messages]
    
    async def clear_session(self, session_id: uuid.UUID):
        """Clear session history."""
        key = self._session_key(session_id)
        await self.redis.delete(key)
    
    async def clear_all(self):
        """Clear all bot memory."""
        pattern = f"bot:{self.bot_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
