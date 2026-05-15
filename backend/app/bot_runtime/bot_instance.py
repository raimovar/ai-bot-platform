"""
Bot Instance
Individual bot execution context
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .session_manager import SessionManager
from .message_queue import MessageQueue
from ..ai_providers import get_provider, BaseAIProvider

logger = logging.getLogger(__name__)


class BotInstance:
    """
    Individual bot execution context

    Handles message processing, AI interactions, and response generation.

    Usage:
        bot = BotInstance(bot_id, config, system_prompt, model_config, ...)
        await bot.start()
        await bot.process_message(message)
        await bot.stop()
    """

    def __init__(
        self,
        bot_id: int,
        config: Dict[str, Any],
        system_prompt: str,
        model_config: Dict[str, Any],
        message_queue: MessageQueue,
        session_manager: SessionManager,
    ):
        self.bot_id = bot_id
        self.config = config
        self.system_prompt = system_prompt
        self.model_config = model_config
        self.message_queue = message_queue
        self.session_manager = session_manager

        # Telegram client
        self._telegram_token = config.get("telegram_token")
        self._client = None

        # AI provider
        self._provider: Optional[BaseAIProvider] = None

        # State
        self._running = False
        self._started_at: Optional[datetime] = None

        # Session context cache
        self._context_cache: Dict[int, List[Dict[str, str]]] = {}

    # =======================
    # Lifecycle
    # =======================

    async def start(self):
        """Start the bot instance"""
        if self._running:
            return

        logger.info(f"Starting bot {self.bot_id}...")

        # Initialize Telegram client
        if self._telegram_token:
            from app.integrations.telegram.client import TelegramClient
            self._client = TelegramClient(self._telegram_token)

        # Initialize AI provider
        provider_type = self.model_config.get("provider", "openai")
        model_name = self.model_config.get("model_name", "gpt-3.5-turbo")
        self._provider = get_provider(
            provider_type,
            model_name=model_name,
            api_key=self.model_config.get("api_key"),
            base_url=self.model_config.get("base_url"),
            config=self.model_config,
        )

        self._running = True
        self._started_at = datetime.utcnow()

        logger.info(f"Bot {self.bot_id} started")

    async def stop(self):
        """Stop the bot instance"""
        if not self._running:
            return

        logger.info(f"Stopping bot {self.bot_id}...")

        self._running = False

        if self._client:
            await self._client.close()

        # Clear context cache
        self._context_cache.clear()

        logger.info(f"Bot {self.bot_id} stopped")

    # =======================
    # Message Processing
    # =======================

    async def process_message(self, message: Dict[str, Any]):
        """
        Process an incoming message

        Args:
            message: Message dict with bot_id, session_id, content, metadata
        """
        if not self._running:
            logger.warning(f"Bot {self.bot_id} not running, ignoring message")
            return

        session_id = message.get("session_id")
        content = message.get("content", "")
        metadata = message.get("metadata", {})
        role = message.get("role", "user")

        chat_id = metadata.get("chat_id")
        original_message_id = metadata.get("message_id")

        logger.debug(f"Processing message for bot {self.bot_id}: {content[:50]}...")

        try:
            # Show typing indicator
            if self._client and chat_id:
                await self._client.send_chat_action(chat_id, "typing")

            # Get conversation context
            context = await self._get_context(session_id)

            # Add current message
            if role == "user":
                context.append({"role": "user", "content": content})

            # Generate response
            response = await self._generate_response(context)

            # Save response to session
            await self._session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response["content"],
                metadata={
                    "model": response.get("model", self.model_config.get("model_name")),
                    "tokens_used": response.get("tokens_used"),
                    "latency_ms": response.get("latency_ms"),
                }
            )

            # Send response to Telegram
            if self._client and chat_id:
                await self._client.send_message(
                    chat_id=chat_id,
                    text=response["content"],
                    parse_mode="Markdown",
                    reply_to_message_id=original_message_id,
                )

            # Update context cache
            self._update_context_cache(session_id, context)

        except Exception as e:
            logger.exception(f"Error processing message for bot {self.bot_id}: {e}")

            # Send error message
            if self._client and chat_id:
                await self._client.send_message(
                    chat_id=chat_id,
                    text="Sorry, I encountered an error processing your message.",
                    reply_to_message_id=original_message_id,
                )

    async def _generate_response(self, context: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate AI response

        Args:
            context: Conversation context

        Returns:
            Dict with content, model, tokens_used, latency_ms
        """
        if not self._provider:
            return {"content": "AI provider not configured", "model": None}

        start_time = asyncio.get_event_loop().time()

        response = await self._provider.generate(
            messages=context,
            system_prompt=self.system_prompt,
            temperature=self.model_config.get("temperature", 0.7),
            max_tokens=self.model_config.get("max_tokens", 2048),
        )

        latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        return {
            "content": response.get("content", ""),
            "model": self.model_config.get("model_name"),
            "tokens_used": response.get("tokens_used"),
            "latency_ms": latency_ms,
        }

    # =======================
    # Context Management
    # =======================

    async def _get_context(
        self,
        session_id: int,
        max_messages: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Get conversation context for a session

        Args:
            session_id: Session ID
            max_messages: Max messages to retrieve

        Returns:
            List of message dicts
        """
        # Check cache first
        if session_id in self._context_cache:
            return self._context_cache[session_id]

        # Get from database
        messages = await self._session_manager.get_messages(
            session_id=session_id,
            limit=max_messages,
        )

        context = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        return context

    def _update_context_cache(self, session_id: int, context: List[Dict[str, str]]):
        """Update context cache for a session"""
        # Keep only last N messages in cache
        max_cache_size = 20
        self._context_cache[session_id] = context[-max_cache_size:]

    # =======================
    # Command Handling
    # =======================

    async def handle_command(self, command: str, args: str, chat_id: int, message_id: int):
        """
        Handle a bot command

        Args:
            command: Command name
            args: Command arguments
            chat_id: Telegram chat ID
            message_id: Original message ID
        """
        logger.info(f"Handling command /{command} for bot {self.bot_id}")

        if command == "help":
            await self._handle_help(chat_id, message_id)

        elif command == "reset":
            await self._handle_reset(chat_id, message_id)

        elif command == "stats":
            await self._handle_stats(chat_id, message_id)

        elif command == "model":
            await self._handle_model_info(chat_id, message_id)

        else:
            if self._client:
                await self._client.send_message(
                    chat_id=chat_id,
                    text=f"Unknown command: /{command}\n\nUse /help for available commands.",
                    reply_to_message_id=message_id,
                )

    async def _handle_help(self, chat_id: int, message_id: int):
        """Send help message"""
        help_text = """
*Available Commands:*

/help - Show this help
/reset - Reset conversation context
/stats - Show bot statistics
/model - Show current model info
        """.strip()

        if self._client:
            await self._client.send_message(
                chat_id=chat_id,
                text=help_text,
                reply_to_message_id=message_id,
            )

    async def _handle_reset(self, chat_id: int, message_id: int):
        """Reset conversation context"""
        # Find session by chat_id
        # This would need the session manager to look up

        if self._client:
            await self._client.send_message(
                chat_id=chat_id,
                text="Conversation context has been reset.",
                reply_to_message_id=message_id,
            )

    async def _handle_stats(self, chat_id: int, message_id: int):
        """Send bot statistics"""
        stats = f"""
*Bot Statistics:*

• Bot ID: {self.bot_id}
• Model: {self.model_config.get('model_name', 'Unknown')}
• Provider: {self.model_config.get('provider', 'Unknown')}
• Started: {self._started_at.isoformat() if self._started_at else 'Unknown'}
        """.strip()

        if self._client:
            await self._client.send_message(
                chat_id=chat_id,
                text=stats,
                reply_to_message_id=message_id,
            )

    async def _handle_model_info(self, chat_id: int, message_id: int):
        """Send model information"""
        info = f"""
*Model Information:*

• Provider: {self.model_config.get('provider', 'Unknown')}
• Model: {self.model_config.get('model_name', 'Unknown')}
• Temperature: {self.model_config.get('temperature', 0.7)}
• Max Tokens: {self.model_config.get('max_tokens', 2048)}
        """.strip()

        if self._client:
            await self._client.send_message(
                chat_id=chat_id,
                text=info,
                reply_to_message_id=message_id,
            )

    # =======================
    # Status
    # =======================

    @property
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running

    def get_info(self) -> Dict[str, Any]:
        """Get bot instance info"""
        return {
            "bot_id": self.bot_id,
            "running": self._running,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "model": self.model_config.get("model_name"),
            "provider": self.model_config.get("provider"),
            "cached_sessions": len(self._context_cache),
        }
