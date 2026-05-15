"""
Telegram Types
Pydantic models for Telegram Bot API
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class UpdateType(str, Enum):
    MESSAGE = "message"
    EDITED_MESSAGE = "edited_message"
    CALLBACK_QUERY = "callback_query"
    CHANNEL_POST = "channel_post"
    EDITED_CHANNEL_POST = "edited_channel_post"


class MessageEntity(BaseModel):
    """Represents one special entity in a text message"""
    type: str
    offset: int
    length: int
    url: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class PhotoSize(BaseModel):
    """Represents a photo"""
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None


class Audio(BaseModel):
    """Represents an audio file"""
    file_id: str
    file_unique_id: str
    duration: int
    performer: Optional[str] = None
    title: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class Voice(BaseModel):
    """Represents a voice note"""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class Document(BaseModel):
    """Represents a general file"""
    file_id: str
    file_unique_id: str
    thumbnail: Optional[PhotoSize] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class Video(BaseModel):
    """Represents a video file"""
    file_id: str
    file_unique_id: str
    width: int
    height: int
    duration: int
    thumbnail: Optional[PhotoSize] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class Contact(BaseModel):
    """Represents a contact"""
    phone_number: str
    first_name: str
    last_name: Optional[str] = None
    user_id: Optional[int] = None
    vcard: Optional[str] = None


class Location(BaseModel):
    """Represents a point on the map"""
    longitude: float
    latitude: float
    horizontal_accuracy: Optional[float] = None
    live_period: Optional[int] = None
    heading: Optional[int] = None
    proximity_alert_radius: Optional[int] = None


class Chat(BaseModel):
    """Represents a chat"""
    id: int
    type: ChatType
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_forum: Optional[bool] = None
    photo: Optional[Dict[str, Any]] = None
    active_usernames: Optional[List[str]] = None
    emoji_status_custom_emoji_id: Optional[str] = None
    bio: Optional[str] = None
    has_private_forum: Optional[bool] = None
    has_hidden_members: Optional[bool] = None
    has_restricted_voice_and_video_messages: Optional[bool] = None
    description: Optional[str] = None
    invite_link: Optional[str] = None
    pinned_message: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    slow_mode_delay: Optional[int] = None
    message_auto_delete_time: Optional[int] = None
    has_aggressive_anti_spam_enabled: Optional[bool] = None
    has_memberscheduled_messages: Optional[bool] = None
    can_set_sticker_set: Optional[bool] = None
    linked_chat_id: Optional[int] = None
    location: Optional[Location] = None


class User(BaseModel):
    """Represents a Telegram user or bot"""
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    added_to_attachment_menu: Optional[bool] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None


class ReplyToMessage(BaseModel):
    """Represents a reply to a message"""
    message_id: int
    from_user: Optional[User] = Field(None, alias="from")
    date: datetime
    chat: Chat
    text: Optional[str] = None


class TelegramMessage(BaseModel):
    """Represents a message"""
    message_id: int
    from_user: Optional[User] = Field(None, alias="from")
    date: datetime
    chat: Chat
    text: Optional[str] = None
    entities: Optional[List[MessageEntity]] = None
    audio: Optional[Audio] = None
    document: Optional[Document] = None
    photo: Optional[List[PhotoSize]] = None
    sticker: Optional[Dict[str, Any]] = None
    video: Optional[Video] = None
    voice: Optional[Voice] = None
    caption: Optional[str] = None
    caption_entities: Optional[List[MessageEntity]] = None
    contact: Optional[Contact] = None
    location: Optional[Location] = None
    reply_to_message: Optional[ReplyToMessage] = None
    via_bot: Optional[User] = None
    edit_date: Optional[datetime] = None
    has_protected_content: Optional[bool] = None
    is_automatic_forward: Optional[bool] = None

    @field_validator("date", "edit_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v

    @property
    def content_text(self) -> str:
        """Get text content, checking caption as fallback"""
        return self.text or self.caption or ""

    @property
    def is_command(self) -> bool:
        """Check if message is a bot command"""
        if self.entities:
            for entity in self.entities:
                if entity.type == "bot_command":
                    return True
        return False

    @property
    def command(self) -> Optional[str]:
        """Extract bot command from message"""
        if self.is_command and self.text:
            # Remove @bot_username if present
            cmd = self.text.split("@")[0]
            return cmd.lstrip("/")
        return None

    class Config:
        populate_by_name = True


class CallbackQuery(BaseModel):
    """Represents a callback query"""
    id: str
    from_user: User = Field(alias="from")
    chat_instance: Optional[str] = None
    message: Optional[TelegramMessage] = None
    inline_message_id: Optional[str] = None
    data: Optional[str] = None

    class Config:
        populate_by_name = True


class InlineQuery(BaseModel):
    """Represents an incoming inline query"""
    id: str
    from_user: User = Field(alias="from")
    query: str
    offset: Optional[str] = None
    chat_type: Optional[ChatType] = None
    location: Optional[Location] = None


class TelegramUpdate(BaseModel):
    """Represents an incoming update from Telegram"""
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
    callback_query: Optional[CallbackQuery] = None
    channel_post: Optional[TelegramMessage] = None
    edited_channel_post: Optional[TelegramMessage] = None
    inline_query: Optional[InlineQuery] = None

    @property
    def effective_message(self) -> Optional[TelegramMessage]:
        """Get the effective message from this update"""
        return (
            self.message
            or self.edited_message
            or self.callback_query.message
            or self.channel_post
            or self.edited_channel_post
        )

    @property
    def update_type(self) -> Optional[UpdateType]:
        """Determine the type of update"""
        if self.message:
            return UpdateType.MESSAGE
        elif self.edited_message:
            return UpdateType.EDITED_MESSAGE
        elif self.callback_query:
            return UpdateType.CALLBACK_QUERY
        elif self.channel_post:
            return UpdateType.CHANNEL_POST
        elif self.edited_channel_post:
            return UpdateType.EDITED_CHANNEL_POST
        return None


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    chat_id: int
    text: str
    parse_mode: Optional[str] = None  # "Markdown" | "MarkdownV2" | "HTML"
    entities: Optional[List[Dict[str, Any]]] = None
    disable_web_page_preview: Optional[bool] = None
    disable_notification: Optional[bool] = None
    reply_to_message_id: Optional[int] = None
    allow_sending_without_reply: Optional[bool] = None
    reply_markup: Optional[Dict[str, Any]] = None


class SendPhotoRequest(BaseModel):
    """Request to send a photo"""
    chat_id: int
    photo: str  # file_id, URL, or file path
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    has_spoiler: Optional[bool] = None
    disable_notification: Optional[bool] = None
    reply_to_message_id: Optional[int] = None
    reply_markup: Optional[Dict[str, Any]] = None


class SendDocumentRequest(BaseModel):
    """Request to send a document"""
    chat_id: int
    document: str  # file_id, URL, or file path
    thumb: Optional[str] = None
    caption: Optional[str] = None
    parse_mode: Optional[str] = None
    disable_content_type_detection: Optional[bool] = None
    disable_notification: Optional[bool] = None
    reply_to_message_id: Optional[int] = None
    reply_markup: Optional[Dict[str, Any]] = None


class InlineKeyboardButton(BaseModel):
    """Inline keyboard button"""
    text: str
    url: Optional[str] = None
    callback_data: Optional[str] = None
    web_app: Optional[Dict[str, Any]] = None
    login_url: Optional[Dict[str, Any]] = None
    switch_inline_query: Optional[str] = None
    switch_inline_query_current_chat: Optional[str] = None
    switch_inline_query_chosen_chat: Optional[Dict[str, Any]] = None
    callback_game: Optional[Dict[str, Any]] = None
    pay: Optional[bool] = None


class InlineKeyboardMarkup(BaseModel):
    """Inline keyboard markup"""
    inline_keyboard: List[List[InlineKeyboardButton]]


class ReplyKeyboardMarkup(BaseModel):
    """Reply keyboard markup"""
    keyboard: List[List[Dict[str, Any]]]
    is_persistent: Optional[bool] = None
    resize_keyboard: Optional[bool] = None
    one_time_keyboard: Optional[bool] = None
    input_field_placeholder: Optional[str] = None
    selective: Optional[bool] = None


class MessageResponse(BaseModel):
    """Response when sending a message"""
    ok: bool
    result: Optional[TelegramMessage] = None
    error_code: Optional[int] = None
    description: Optional[str] = None


class BotInfo(BaseModel):
    """Information about a bot"""
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: str
    can_join_groups: bool
    can_read_all_group_messages: bool
    supports_inline_queries: bool


class SetWebhookRequest(BaseModel):
    """Request to set webhook"""
    url: str
    certificate: Optional[str] = None
    ip_address: Optional[str] = None
    max_connections: Optional[int] = 40
    allowed_updates: Optional[List[str]] = None
    drop_pending_updates: Optional[bool] = None
    secret_token: Optional[str] = None


class WebhookInfo(BaseModel):
    """Information about webhook status"""
    url: Optional[str] = None
    has_custom_certificate: bool
    pending_update_count: int
    ip_address: Optional[str] = None
    last_error_date: Optional[datetime] = None
    last_error_message: Optional[str] = None
    max_connections: Optional[int] = None
    allowed_updates: Optional[List[str]] = None
    is_disabled: Optional[bool] = None
