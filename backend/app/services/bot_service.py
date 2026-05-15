"""
Bot service - business logic for bot operations.
"""
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bot import Bot, BotTool


class BotService:
    """Service for bot-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_bot_with_tools(self, bot_id: uuid.UUID) -> Optional[Bot]:
        """Get bot with all tools loaded."""
        result = await self.db.execute(
            select(Bot)
            .options(selectinload(Bot.tools))
            .where(Bot.id == bot_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_bots(self) -> list[Bot]:
        """Get all active (running) bots."""
        result = await self.db.execute(
            select(Bot)
            .options(selectinload(Bot.tools))
            .where(Bot.is_active == True, Bot.status == "running")
        )
        return list(result.scalars().all())
    
    async def get_enabled_tools(self, bot_id: uuid.UUID) -> list[BotTool]:
        """Get all enabled tools for a bot."""
        result = await self.db.execute(
            select(BotTool).where(
                BotTool.bot_id == bot_id,
                BotTool.is_enabled == True
            ).order_by(BotTool.priority)
        )
        return list(result.scalars().all())
    
    def build_system_prompt(
        self,
        bot: Bot,
        context: Optional[dict] = None
    ) -> str:
        """Build complete system prompt with context."""
        prompt = bot.system_prompt
        
        # Add context if provided
        if context:
            if context.get("user_name"):
                prompt += f"\n\nUser name: {context['user_name']}"
            if context.get("session_history"):
                prompt += "\n\nRecent conversation:\n"
                for msg in context["session_history"][-5:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    prompt += f"\n{role}: {content[:200]}"
        
        return prompt
    
    async def validate_telegram_token(self, token: str) -> bool:
        """Validate a Telegram bot token."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=10.0
                )
                return response.json().get("ok", False)
        except Exception:
            return False
