"""
Telegram Bot Base Classes
Telegram Bot API integration layer
"""

from .client import TelegramClient
from .webhook import WebhookHandler
from .polling import PollingConsumer
from .router import TelegramRouter
from .types import TelegramUpdate, TelegramMessage, TelegramCallbackQuery

__all__ = [
    "TelegramClient",
    "WebhookHandler",
    "PollingConsumer",
    "TelegramRouter",
    "TelegramUpdate",
    "TelegramMessage",
    "TelegramCallbackQuery",
]
