"""
Telegram Message Router
Routes incoming messages to appropriate handlers
"""

import logging
import re
from typing import Optional, Callable, Awaitable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from .types import TelegramUpdate, TelegramMessage, CallbackQuery, UpdateType
from .client import TelegramClient, inline_keyboard, keyboard_button

logger = logging.getLogger(__name__)


class UpdatePriority(int, Enum):
    """Priority levels for handlers"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Command:
    """Bot command definition"""
    name: str
    handler: Callable[[TelegramMessage, TelegramClient], Awaitable[None]]
    description: Optional[str] = None
    pattern: Optional[str] = None  # Regex pattern instead of exact match


@dataclass
class MessageHandler:
    """Message handler with filters"""
    name: str
    handler: Callable[[TelegramMessage, TelegramClient], Awaitable[None]]
    filters: Dict[str, Any] = field(default_factory=dict)
    priority: UpdatePriority = UpdatePriority.NORMAL


@dataclass
class CallbackHandler:
    """Callback query handler"""
    name: str
    handler: Callable[[CallbackQuery, TelegramClient], Awaitable[None]]
    pattern: Optional[str] = None  # Regex pattern to match callback_data


class TelegramRouter:
    """
    Message router for Telegram bots

    Handles command routing, message filtering, and callback queries.

    Usage:
        router = TelegramRouter(bot_token)

        # Add command handlers
        @router.command("/start")
        async def handle_start(message, client):
            await client.send_message(message.chat.id, "Hello!")

        # Add message handlers
        @router.message(filters={"text_contains": "hello"})
        async def handle_hello(message, client):
            ...

        # Add callback handlers
        @router.callback("confirm_")
        async def handle_confirm(query, client):
            ...

        # Process updates
        await router.process_update(update)
    """

    def __init__(self, bot_token: str, bot_id: int):
        self.bot_token = bot_token
        self.bot_id = bot_id
        self._client: Optional[TelegramClient] = None

        # Command handlers: {command_name: handler}
        self._commands: Dict[str, Command] = {}

        # Message handlers with filters
        self._message_handlers: List[MessageHandler] = []

        # Callback handlers
        self._callback_handlers: List[CallbackHandler] = []

        # Default handlers
        self._default_command_handler: Optional[Callable] = None
        self._default_message_handler: Optional[Callable] = None

        # Registered bot commands for /help menu
        self._bot_commands: List[Dict[str, str]] = []

        # Statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.callbacks_received = 0
        self.callbacks_processed = 0

    @property
    def client(self) -> TelegramClient:
        """Get or create Telegram client"""
        if not self._client:
            self._client = TelegramClient(self.bot_token)
        return self._client

    # =======================
    # Decorators
    # =======================

    def command(
        self,
        name: str,
        description: Optional[str] = None,
        pattern: Optional[str] = None,
    ):
        """
        Decorator to register a command handler

        Args:
            name: Command name (with or without /)
            description: Command description for /help
            pattern: Optional regex pattern for dynamic commands

        Usage:
            @router.command("/start")
            async def start(message, client):
                ...

            @router.command(r"/user_(\d+)", pattern=True)
            async def user_id(message, client):
                ...
        """
        def decorator(func: Callable):
            cmd_name = name.lstrip("/")

            self._commands[cmd_name] = Command(
                name=cmd_name,
                handler=func,
                description=description,
                pattern=pattern,
            )

            # Register for /help menu
            if description:
                self._bot_commands.append({
                    "command": cmd_name,
                    "description": description,
                })

            return func

        return decorator

    def message(self, filters: Optional[Dict[str, Any]] = None):
        """
        Decorator to register a message handler

        Filters:
            - text_contains: Message contains text
            - text_startswith: Message starts with text
            - regex: Match regex pattern
            - has_photo: Message has photo
            - has_document: Message has document
            - has_location: Message has location
            - from_user_id: Specific user ID
            - chat_type: Specific chat type

        Usage:
            @router.message(filters={"text_contains": "hello"})
            async def handle_hello(message, client):
                ...
        """
        def decorator(func: Callable):
            self._message_handlers.append(MessageHandler(
                name=func.__name__,
                handler=func,
                filters=filters or {},
            ))
            return func

        return decorator

    def callback(self, pattern: str = ""):
        """
        Decorator to register a callback query handler

        Args:
            pattern: Regex pattern to match callback_data

        Usage:
            @router.callback("confirm_")
            async def handle_confirm(query, client):
                await client.answer_callback_query(query.id, "Confirmed!")
        """
        def decorator(func: Callable):
            self._callback_handlers.append(CallbackHandler(
                name=func.__name__,
                handler=func,
                pattern=pattern if pattern else None,
            ))
            return func

        return decorator

    def default_command(self, func: Callable):
        """Decorator for default command handler (unrecognized commands)"""
        self._default_command_handler = func
        return func

    def default_message(self, func: Callable):
        """Decorator for default message handler (all other messages)"""
        self._default_message_handler = func
        return func

    # =======================
    # Processing
    # =======================

    async def process_update(self, update: TelegramUpdate) -> bool:
        """
        Process an incoming update

        Args:
            update: Telegram update to process

        Returns:
            True if update was handled
        """
        update_type = update.update_type

        if update_type == UpdateType.MESSAGE or update_type == UpdateType.CHANNEL_POST:
            return await self._handle_message(update.effective_message)

        elif update_type == UpdateType.EDITED_MESSAGE:
            message = update.effective_message
            logger.debug(f"Edited message {message.message_id}")
            return True

        elif update_type == UpdateType.CALLBACK_QUERY:
            return await self._handle_callback(update.callback_query)

        elif update_type == UpdateType.EDITED_CHANNEL_POST:
            return True

        return False

    async def _handle_message(self, message: Optional[TelegramMessage]) -> bool:
        """Handle incoming message"""
        if not message:
            return False

        self.messages_received += 1

        # Check if it's a command
        if message.is_command:
            command = message.command
            if command:
                handled = await self._handle_command(command, message)
                if handled:
                    self.messages_processed += 1
                    return True

        # Try message handlers
        for handler in sorted(self._message_handlers, key=lambda h: h.priority.value, reverse=True):
            if await self._match_filters(message, handler.filters):
                try:
                    await handler.handler(message, self.client)
                    self.messages_processed += 1
                    return True
                except Exception as e:
                    logger.exception(f"Handler error: {e}")

        # Try default handler
        if self._default_message_handler:
            try:
                await self._default_message_handler(message, self.client)
                self.messages_processed += 1
                return True
            except Exception as e:
                logger.exception(f"Default handler error: {e}")

        return False

    async def _handle_command(self, command: str, message: TelegramMessage) -> bool:
        """Handle a bot command"""
        # Direct command match
        if command in self._commands:
            handler = self._commands[command]
            try:
                await handler.handler(message, self.client)
                return True
            except Exception as e:
                logger.exception(f"Command handler error: {e}")
                return False

        # Pattern match
        for cmd in self._commands.values():
            if cmd.pattern:
                try:
                    if re.match(cmd.pattern, command):
                        await cmd.handler(message, self.client)
                        return True
                except Exception as e:
                    logger.exception(f"Pattern handler error: {e}")

        # Default handler
        if self._default_command_handler:
            try:
                await self._default_command_handler(message, self.client)
                return True
            except Exception as e:
                logger.exception(f"Default command error: {e}")

        return False

    async def _handle_callback(self, query: Optional[CallbackQuery]) -> bool:
        """Handle callback query"""
        if not query or not query.data:
            return False

        self.callbacks_received += 1

        # Try pattern handlers
        for handler in self._callback_handlers:
            if handler.pattern:
                if re.match(handler.pattern, query.data):
                    try:
                        await handler.handler(query, self.client)
                        self.callbacks_processed += 1
                        return True
                    except Exception as e:
                        logger.exception(f"Callback handler error: {e}")

        # Try exact match
        for handler in self._callback_handlers:
            if not handler.pattern and handler.name == query.data:
                try:
                    await handler.handler(query, self.client)
                    self.callbacks_processed += 1
                    return True
                except Exception as e:
                    logger.exception(f"Callback handler error: {e}")

        # No handler found - answer with error
        try:
            await self.client.answer_callback_query(
                query.id,
                text="Unknown action",
                show_alert=False,
            )
        except Exception:
            pass

        return False

    async def _match_filters(
        self, message: TelegramMessage, filters: Dict[str, Any]
    ) -> bool:
        """Check if message matches filters"""
        if not filters:
            return False

        for filter_name, filter_value in filters.items():
            if filter_name == "text_contains":
                if not message.content_text or filter_value not in message.content_text:
                    return False

            elif filter_name == "text_startswith":
                if not message.content_text or not message.content_text.startswith(filter_value):
                    return False

            elif filter_name == "text_equals":
                if message.content_text != filter_value:
                    return False

            elif filter_name == "regex":
                if not message.content_text or not re.search(filter_value, message.content_text):
                    return False

            elif filter_name == "has_photo":
                if not message.photo:
                    return False

            elif filter_name == "has_document":
                if not message.document:
                    return False

            elif filter_name == "has_location":
                if not message.location:
                    return False

            elif filter_name == "has_audio":
                if not message.audio:
                    return False

            elif filter_name == "has_video":
                if not message.video:
                    return False

            elif filter_name == "has_voice":
                if not message.voice:
                    return False

            elif filter_name == "has_sticker":
                if not message.sticker:
                    return False

            elif filter_name == "has_reply":
                if not message.reply_to_message:
                    return False

            elif filter_name == "from_user_id":
                if not message.from_user or message.from_user.id != filter_value:
                    return False

            elif filter_name == "chat_type":
                if message.chat.type.value != filter_value:
                    return False

            elif filter_name == "chat_id":
                if message.chat.id != filter_value:
                    return False

        return True

    # =======================
    # Bot Commands Menu
    # =======================

    async def set_commands_menu(self):
        """Register commands with Telegram"""
        if self._bot_commands:
            await self.client.set_my_commands(self._bot_commands)

    # =======================
    # Utility Methods
    # =======================

    def get_stats(self) -> dict:
        """Get router statistics"""
        return {
            "commands_registered": len(self._commands),
            "message_handlers": len(self._message_handlers),
            "callback_handlers": len(self._callback_handlers),
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "callbacks_received": self.callbacks_received,
            "callbacks_processed": self.callbacks_processed,
        }

    async def close(self):
        """Close router resources"""
        if self._client:
            await self._client.close()
