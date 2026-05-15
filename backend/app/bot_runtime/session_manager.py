"""
Session Manager
Manages bot sessions and conversation context
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages bot sessions and conversation context

    Handles:
    - Session lifecycle
    - Message history
    - Short-term memory (Redis)
    - Long-term memory (PostgreSQL)

    Usage:
        manager = SessionManager(db_url, redis_url)
        await manager.connect()

        # Get or create session
        session = await manager.get_or_create_session(...)

        # Add message
        await manager.add_message(session_id, role, content)

        # Get context
        messages = await manager.get_messages(session_id)

        # Cleanup
        await manager.cleanup_stale_sessions()
    """

    def __init__(
        self,
        db_url: str,
        redis_url: str = "redis://localhost:6379/0",
        context_ttl: int = 3600,  # 1 hour
        max_context_messages: int = 50,
    ):
        self.db_url = db_url
        self.redis_url = redis_url
        self.context_ttl = context_ttl
        self.max_context_messages = max_context_messages

        self._redis: Optional[redis.Redis] = None
        self._db_session: Optional[AsyncSession] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis and initialize database session"""
        if self._connected:
            return

        # Connect to Redis
        self._redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()

        # Import here to avoid circular imports
        from app.core.database import async_session_maker
        self._db_session = async_session_maker()

        self._connected = True
        logger.info("Session manager connected")

    async def disconnect(self):
        """Disconnect from Redis and close database session"""
        if self._redis:
            await self._redis.close()
            self._redis = None

        if self._db_session:
            await self._db_session.close()
            self._db_session = None

        self._connected = False
        logger.info("Session manager disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self._redis is not None

    # =======================
    # Session Operations
    # =======================

    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        from app.models.session import Session

        result = await self._db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            return {
                "id": session.id,
                "bot_id": session.bot_id,
                "external_id": session.external_id,
                "chat_type": session.chat_type,
                "chat_title": session.chat_title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        return None

    async def create_session(
        self,
        bot_id: int,
        external_id: str,
        chat_type: str = "private",
        chat_title: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> int:
        """
        Create a new session

        Returns:
            Session ID
        """
        from app.models.session import Session

        session = Session(
            bot_id=bot_id,
            external_id=external_id,
            chat_type=chat_type,
            chat_title=chat_title,
            username=username,
            first_name=first_name,
        )

        self._db_session.add(session)
        await self._db_session.commit()
        await self._db_session.refresh(session)

        logger.debug(f"Created session {session.id} for bot {bot_id}")
        return session.id

    async def get_or_create_session(
        self,
        bot_id: int,
        external_id: str,
        chat_type: str = "private",
        chat_title: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> int:
        """Get existing session or create new one"""
        from app.models.session import Session

        # Try to find existing
        result = await self._db_session.execute(
            select(Session).where(
                Session.bot_id == bot_id,
                Session.external_id == external_id,
            )
        )
        session = result.scalar_one_or_none()

        if session:
            # Update chat info
            session.chat_type = chat_type
            if chat_title:
                session.chat_title = chat_title
            session.username = username
            session.first_name = first_name
            await self._db_session.commit()
            return session.id

        # Create new
        return await self.create_session(
            bot_id=bot_id,
            external_id=external_id,
            chat_type=chat_type,
            chat_title=chat_title,
            username=username,
            first_name=first_name,
        )

    # =======================
    # Message Operations
    # =======================

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add a message to session history

        Returns:
            Message ID
        """
        from app.models.message import Message

        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self._db_session.add(message)
        await self._db_session.commit()
        await self._db_session.refresh(message)

        # Update session timestamp
        await self._update_session_timestamp(session_id)

        # Update context cache
        await self._cache_message(session_id, role, content)

        return message.id

    async def get_messages(
        self,
        session_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        from app.models.message import Message

        result = await self._db_session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = result.scalars().all()

        # Return in chronological order
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "model": m.model,
                "tokens_used": m.tokens_used,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(list(messages))
        ]

    # =======================
    # Context Cache (Redis)
    # =======================

    def _get_cache_key(self, session_id: int) -> str:
        """Get Redis cache key for session"""
        return f"session:{session_id}:context"

    async def _cache_message(self, session_id: int, role: str, content: str):
        """Add message to context cache"""
        if not self._redis:
            return

        try:
            cache_key = self._get_cache_key(session_id)

            # Add to list
            import json
            message_json = json.dumps({"role": role, "content": content})
            await self._redis.rpush(cache_key, message_json)

            # Trim to max size
            await self._redis.ltrim(cache_key, -self.max_context_messages, -1)

            # Set TTL
            await self._redis.expire(cache_key, self.context_ttl)

        except Exception as e:
            logger.warning(f"Failed to cache message: {e}")

    async def get_cached_context(self, session_id: int) -> Optional[List[Dict[str, str]]]:
        """Get cached context from Redis"""
        if not self._redis:
            return None

        try:
            cache_key = self._get_cache_key(session_id)
            messages = await self._redis.lrange(cache_key, 0, -1)

            if not messages:
                return None

            import json
            return [json.loads(m) for m in messages]

        except Exception as e:
            logger.warning(f"Failed to get cached context: {e}")
            return None

    async def clear_context_cache(self, session_id: int):
        """Clear context cache for a session"""
        if not self._redis:
            return

        try:
            cache_key = self._get_cache_key(session_id)
            await self._redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to clear context cache: {e}")

    # =======================
    # Session Metadata
    # =======================

    async def set_session_metadata(
        self,
        session_id: int,
        key: str,
        value: Any,
    ):
        """Set session metadata"""
        if not self._redis:
            return

        try:
            meta_key = f"session:{session_id}:meta"
            import json
            await self._redis.hset(meta_key, key, json.dumps(value))
            await self._redis.expire(meta_key, self.context_ttl)
        except Exception as e:
            logger.warning(f"Failed to set session metadata: {e}")

    async def get_session_metadata(
        self,
        session_id: int,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get session metadata"""
        if not self._redis:
            return default

        try:
            meta_key = f"session:{session_id}:meta"
            import json
            value = await self._redis.hget(meta_key, key)
            return json.loads(value) if value else default
        except Exception as e:
            logger.warning(f"Failed to get session metadata: {e}")
            return default

    # =======================
    # Cleanup
    # =======================

    async def _update_session_timestamp(self, session_id: int):
        """Update session updated_at timestamp"""
        from app.models.session import Session

        await self._db_session.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(updated_at=datetime.utcnow())
        )
        await self._db_session.commit()

    async def cleanup_stale_sessions(self, max_age_days: int = 30):
        """Delete stale sessions"""
        from app.models.session import Session

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        # Delete old sessions
        result = await self._db_session.execute(
            delete(Session)
            .where(Session.updated_at < cutoff)
        )
        await self._db_session.commit()

        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} stale sessions")

        return deleted_count

    # =======================
    # Statistics
    # =======================

    async def get_session_count(self, bot_id: Optional[int] = None) -> int:
        """Get total session count"""
        from app.models.session import Session

        query = select(Session)
        if bot_id:
            query = query.where(Session.bot_id == bot_id)

        result = await self._db_session.execute(query)
        return len(result.scalars().all())

    async def get_message_count(self, session_id: int) -> int:
        """Get message count for a session"""
        from app.models.message import Message

        result = await self._db_session.execute(
            select(Message)
            .where(Message.session_id == session_id)
        )
        return len(result.scalars().all())
