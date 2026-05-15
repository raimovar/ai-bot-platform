"""
Bot Manager - Manages lifecycle of all bot instances.
"""
import uuid
from typing import Dict, Optional
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.engine.bot_instance import BotInstance


class BotManager:
    """
    Manages all running bot instances.
    
    Responsibilities:
    - Start/stop bots
    - Track running bots
    - Load bot configuration
    - Handle bot lifecycle
    """
    
    def __init__(
        self,
        db_url: str,
        redis_client,
        ai_gateway_url: str,
    ):
        self.db_url = db_url
        self.redis = redis_client
        self.ai_gateway_url = ai_gateway_url
        
        # Create async engine
        self.engine = create_async_engine(db_url, pool_pre_ping=True)
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Running bots
        self.running_bots: Dict[uuid.UUID, BotInstance] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def start_bot(self, bot_id: uuid.UUID) -> BotInstance:
        """Start a bot."""
        async with self._lock:
            if bot_id in self.running_bots:
                return self.running_bots[bot_id]
            
            # Load bot configuration from database
            config = await self._load_bot_config(bot_id)
            
            if not config:
                raise ValueError(f"Bot {bot_id} not found")
            
            # Create bot instance
            async with self.session_maker() as session:
                bot_instance = BotInstance(
                    bot_id=bot_id,
                    config=config,
                    db_session=session,
                    redis_client=self.redis,
                    ai_gateway_url=self.ai_gateway_url,
                )
                
                await bot_instance.start()
                
                self.running_bots[bot_id] = bot_instance
                
                # Update status in database
                await self._update_bot_status(bot_id, "running")
                
                return bot_instance
    
    async def stop_bot(self, bot_id: uuid.UUID):
        """Stop a bot."""
        async with self._lock:
            if bot_id not in self.running_bots:
                return
            
            bot_instance = self.running_bots[bot_id]
            await bot_instance.stop()
            
            del self.running_bots[bot_id]
            
            await self._update_bot_status(bot_id, "stopped")
    
    async def stop_all(self):
        """Stop all running bots."""
        for bot_id in list(self.running_bots.keys()):
            await self.stop_bot(bot_id)
    
    async def get_bot(self, bot_id: uuid.UUID) -> Optional[BotInstance]:
        """Get a bot instance, starting it if needed."""
        if bot_id not in self.running_bots:
            try:
                await self.start_bot(bot_id)
            except Exception as e:
                print(f"Failed to start bot {bot_id}: {e}")
                return None
        
        return self.running_bots.get(bot_id)
    
    def is_running(self, bot_id: uuid.UUID) -> bool:
        """Check if a bot is running."""
        return bot_id in self.running_bots
    
    async def _load_bot_config(self, bot_id: uuid.UUID) -> Optional[dict]:
        """Load bot configuration from database."""
        from app.models.bot import Bot, BotTool
        
        async with self.session_maker() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                return None
            
            # Get tools
            tools_result = await session.execute(
                select(BotTool).where(
                    BotTool.bot_id == bot_id,
                    BotTool.is_enabled == True,
                )
            )
            tools = tools_result.scalars().all()
            
            # Build config
            config = {
                "name": bot.name,
                "provider": bot.provider,
                "model_name": bot.model_name,
                "temperature": float(bot.temperature),
                "max_tokens": bot.max_tokens,
                "system_prompt": bot.system_prompt,
                "memory_type": bot.memory_type,
                "memory_config": bot.memory_config or {},
                "telegram_token": bot.telegram_token,
                "telegram_enabled": bot.telegram_enabled,
                "tools": [
                    {
                        "name": t.tool_name,
                        "type": t.tool_type,
                        "config": t.config or {},
                        "definition": t.definition,
                    }
                    for t in tools
                ],
            }
            
            return config
    
    async def _update_bot_status(self, bot_id: uuid.UUID, status: str):
        """Update bot status in database."""
        from app.models.bot import Bot
        from datetime import datetime, timezone
        
        async with self.session_maker() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if bot:
                bot.status = status
                if status == "running":
                    bot.last_started = datetime.now(timezone.utc)
                await session.commit()
