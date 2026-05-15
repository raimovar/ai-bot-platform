"""
Telegram Bot Client
HTTP client for Telegram Bot API
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .types import (
    SendMessageRequest,
    SendPhotoRequest,
    SendDocumentRequest,
    TelegramMessage,
    BotInfo,
    WebhookInfo,
    SetWebhookRequest,
    MessageResponse,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

logger = logging.getLogger(__name__)


class TelegramAPIError(Exception):
    """Telegram API Error"""

    def __init__(self, error_code: int, description: str):
        self.error_code = error_code
        self.description = description
        super().__init__(f"Telegram API Error {error_code}: {description}")


class RateLimitError(TelegramAPIError):
    """Rate limit exceeded"""
    pass


class TelegramClient:
    """
    Async client for Telegram Bot API

    Usage:
        client = TelegramClient(bot_token="123:ABC")
        info = await client.get_me()
        await client.send_message(chat_id=123, text="Hello!")
    """

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(
        self,
        bot_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_delay: float = 1.0,
    ):
        self.bot_token = bot_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._last_request_time: float = 0

        # Rate limiting: max ~30 messages per second
        self._min_interval = 0.035  # ~28 messages/sec with some margin

    @property
    def _client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client"""
        if not hasattr(self, "_http_client"):
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._http_client

    def _get_url(self, method: str) -> str:
        """Build URL for API method"""
        return self.BASE_URL.format(token=self.bot_token, method=method)

    async def close(self):
        """Close HTTP client"""
        if hasattr(self, "_http_client"):
            await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic

        Args:
            method: API method name
            data: Request data
            files: Files to upload

        Returns:
            API response

        Raises:
            TelegramAPIError: On API errors
            RateLimitError: On rate limit
        """
        url = self._get_url(method)

        try:
            if files:
                # Multipart request for files
                form_data = {}
                for k, v in (data or {}).items():
                    if v is not None:
                        form_data[k] = str(v) if not isinstance(v, str) else v
                for k, v in files.items():
                    form_data[k] = v

                response = await self._client.post(
                    url,
                    files=form_data,
                )
            else:
                # JSON request
                response = await self._client.post(
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                )

            response.raise_for_status()
            result = response.json()

            if not result.get("ok", False):
                error_code = result.get("error_code", 400)
                description = result.get("description", "Unknown error")

                if error_code == 429:
                    retry_after = result.get("parameters", {}).get("retry_after", 60)
                    logger.warning(f"Rate limited, retry after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise RateLimitError(error_code, description)

                raise TelegramAPIError(error_code, description)

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(
                    e.response.headers.get("Retry-After", 60)
                )
                logger.warning(f"Rate limited, retry after {retry_after}s")
                await asyncio.sleep(retry_after)
                raise RateLimitError(429, "Too Many Requests")
            raise

        except httpx.TimeoutException:
            logger.warning(f"Timeout for {method}, retrying...")
            raise

    async def _rate_limited_request(
        self,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply rate limiting before request"""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time

        if time_since_last < self._min_interval:
            await asyncio.sleep(self._min_interval - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()
        return await self._request(method, data, files)

    # =======================
    # Bot Information
    # =======================

    async def get_me(self) -> BotInfo:
        """
        Get basic information about the bot

        Returns:
            BotInfo with bot details
        """
        result = await self._request("getMe")
        return BotInfo(**result["result"])

    async def get_bot_name(self) -> Dict[str, str]:
        """Get bot name"""
        result = await self._request("getMyName")
        return result["result"]

    async def set_my_name(self, name: str, language_code: Optional[str] = None):
        """Set bot name"""
        data = {"name": name}
        if language_code:
            data["language_code"] = language_code
        await self._request("setMyName", data)

    async def set_my_description(
        self, description: str, language_code: Optional[str] = None
    ):
        """Set bot description"""
        data = {"description": description}
        if language_code:
            data["language_code"] = language_code
        await self._request("setMyDescription", data)

    async def set_my_short_description(
        self, short_description: str, language_code: Optional[str] = None
    ):
        """Set bot short description"""
        data = {"short_description": short_description}
        if language_code:
            data["language_code"] = language_code
        await self._request("setMyShortDescription", data)

    async def set_my_commands(
        self,
        commands: List[Dict[str, str]],
        language_code: Optional[str] = None,
    ):
        """Set bot commands"""
        data = {"commands": commands}
        if language_code:
            data["language_code"] = language_code
        await self._request("setMyCommands", data)

    async def get_my_commands(self, language_code: Optional[str] = None) -> List[Dict[str, str]]:
        """Get bot commands"""
        data = {}
        if language_code:
            data["language_code"] = language_code
        result = await self._request("getMyCommands", data if data else None)
        return result.get("result", [])

    # =======================
    # Sending Messages
    # =======================

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = "Markdown",
        entities: Optional[List[Dict[str, Any]]] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: bool = True,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """
        Send a text message

        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: "Markdown", "MarkdownV2", or "HTML"
            entities: List of message entities for custom text formatting
            disable_web_page_preview: Disable link previews
            disable_notification: Send silently
            reply_to_message_id: Reply to specific message
            allow_sending_without_reply: Allow sending even if replied message is gone
            reply_markup: Inline keyboard or reply keyboard

        Returns:
            Sent message
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
            "allow_sending_without_reply": allow_sending_without_reply,
        }

        if entities:
            data["entities"] = entities
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._rate_limited_request("sendMessage", data)
        return TelegramMessage(**result["result"])

    async def send_photo(
        self,
        chat_id: int,
        photo: Union[str, bytes],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "Markdown",
        has_spoiler: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """
        Send a photo

        Args:
            chat_id: Target chat ID
            photo: Photo (file_id, URL, or bytes)
            caption: Photo caption
            parse_mode: "Markdown", "MarkdownV2", or "HTML"
            has_spoiler: Mark as spoiler
            disable_notification: Send silently
            reply_to_message_id: Reply to specific message
            reply_markup: Inline keyboard

        Returns:
            Sent message
        """
        data = {
            "chat_id": chat_id,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification,
        }

        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        # Handle photo as URL or file_id
        if isinstance(photo, str) and not photo.startswith("attach://"):
            data["photo"] = photo
            result = await self._rate_limited_request("sendPhoto", data)
        else:
            files = {"photo": photo} if isinstance(photo, bytes) else {}
            result = await self._rate_limited_request("sendPhoto", data, files)

        return TelegramMessage(**result["result"])

    async def send_document(
        self,
        chat_id: int,
        document: Union[str, bytes],
        thumb: Optional[Union[str, bytes]] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "Markdown",
        disable_content_type_detection: bool = False,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Send a document"""
        data = {
            "chat_id": chat_id,
            "disable_content_type_detection": disable_content_type_detection,
            "disable_notification": disable_notification,
        }

        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        files = {}
        if isinstance(document, bytes):
            files["document"] = document
        if thumb and isinstance(thumb, bytes):
            files["thumb"] = thumb

        if files:
            result = await self._rate_limited_request("sendDocument", data, files)
        else:
            data["document"] = document
            result = await self._rate_limited_request("sendDocument", data)

        return TelegramMessage(**result["result"])

    async def send_sticker(
        self,
        chat_id: int,
        sticker: str,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Send a sticker"""
        data = {
            "chat_id": chat_id,
            "sticker": sticker,
            "disable_notification": disable_notification,
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._rate_limited_request("sendSticker", data)
        return TelegramMessage(**result["result"])

    async def send_video(
        self,
        chat_id: int,
        video: Union[str, bytes],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "Markdown",
        has_spoiler: bool = False,
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Send a video"""
        data = {
            "chat_id": chat_id,
            "video": video,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification,
        }

        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if duration:
            data["duration"] = duration
        if width:
            data["width"] = width
        if height:
            data["height"] = height
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        files = {"video": video} if isinstance(video, bytes) else {}
        if files:
            result = await self._rate_limited_request("sendVideo", data, files)
        else:
            result = await self._rate_limited_request("sendVideo", data)

        return TelegramMessage(**result["result"])

    async def send_location(
        self,
        chat_id: int,
        latitude: float,
        longitude: float,
        horizontal_accuracy: Optional[float] = None,
        live_period: Optional[int] = None,
        heading: Optional[int] = None,
        proximity_alert_radius: Optional[int] = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Send a location"""
        data = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "disable_notification": disable_notification,
        }

        if horizontal_accuracy is not None:
            data["horizontal_accuracy"] = horizontal_accuracy
        if live_period:
            data["live_period"] = live_period
        if heading:
            data["heading"] = heading
        if proximity_alert_radius:
            data["proximity_alert_radius"] = proximity_alert_radius
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._rate_limited_request("sendLocation", data)
        return TelegramMessage(**result["result"])

    async def send_contact(
        self,
        chat_id: int,
        phone_number: str,
        first_name: str,
        last_name: Optional[str] = None,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Send a contact"""
        data = {
            "chat_id": chat_id,
            "phone_number": phone_number,
            "first_name": first_name,
            "disable_notification": disable_notification,
        }

        if last_name:
            data["last_name"] = last_name
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._rate_limited_request("sendContact", data)
        return TelegramMessage(**result["result"])

    async def send_chat_action(
        self,
        chat_id: int,
        action: str = "typing",
    ) -> bool:
        """
        Send a chat action

        Actions: typing, upload_photo, record_video, upload_video,
                record_voice, upload_voice, upload_document, choose_sticker,
                find_location, recording_video_note, upload_video_note
        """
        data = {"chat_id": chat_id, "action": action}
        result = await self._request("sendChatAction", data)
        return result.get("result", False)

    # =======================
    # Editing Messages
    # =======================

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: Optional[str] = "Markdown",
        entities: Optional[List[Dict[str, Any]]] = None,
        disable_web_page_preview: Optional[bool] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Edit message text"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        if entities:
            data["entities"] = entities
        if disable_web_page_preview is not None:
            data["disable_web_page_preview"] = disable_web_page_preview
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._request("editMessageText", data)
        return TelegramMessage(**result["result"])

    async def edit_message_caption(
        self,
        chat_id: int,
        message_id: int,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "Markdown",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Edit message caption"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._request("editMessageCaption", data)
        return TelegramMessage(**result["result"])

    async def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> TelegramMessage:
        """Edit message reply markup"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._request("editMessageReplyMarkup", data)
        return TelegramMessage(**result["result"])

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message"""
        data = {"chat_id": chat_id, "message_id": message_id}
        result = await self._request("deleteMessage", data)
        return result.get("result", False)

    # =======================
    # Inline Mode
    # =======================

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
        url: Optional[str] = None,
        cache_time: Optional[int] = None,
    ) -> bool:
        """
        Answer a callback query

        Args:
            callback_query_id: Query ID
            text: Text to show (max 200 chars for alert, 256 otherwise)
            show_alert: Show as alert instead of toast
            url: Open URL after button press
            cache_time: Cache duration
        """
        data = {"callback_query_id": callback_query_id, "show_alert": show_alert}

        if text:
            data["text"] = text
        if url:
            data["url"] = url
        if cache_time is not None:
            data["cache_time"] = cache_time

        result = await self._request("answerCallbackQuery", data)
        return result.get("result", False)

    async def answer_inline_query(
        self,
        inline_query_id: str,
        results: List[Dict[str, Any]],
        cache_time: int = 300,
        is_personal: bool = False,
        next_offset: Optional[str] = None,
        switch_pm_text: Optional[str] = None,
        switch_pm_parameter: Optional[str] = None,
    ) -> bool:
        """Answer an inline query"""
        data = {
            "inline_query_id": inline_query_id,
            "results": results,
            "cache_time": cache_time,
            "is_personal": is_personal,
        }

        if next_offset:
            data["next_offset"] = next_offset
        if switch_pm_text:
            data["switch_pm_text"] = switch_pm_text
        if switch_pm_parameter:
            data["switch_pm_parameter"] = switch_pm_parameter

        result = await self._request("answerInlineQuery", data)
        return result.get("result", False)

    # =======================
    # Chat Management
    # =======================

    async def get_chat(self, chat_id: int) -> Dict[str, Any]:
        """Get chat information"""
        data = {"chat_id": chat_id}
        result = await self._request("getChat", data)
        return result["result"]

    async def get_chat_administrators(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get chat administrators"""
        data = {"chat_id": chat_id}
        result = await self._request("getChatAdministrators", data)
        return result.get("result", [])

    async def get_chat_member_count(self, chat_id: int) -> int:
        """Get chat member count"""
        data = {"chat_id": chat_id}
        result = await self._request("getChatMemberCount", data)
        return result.get("result", 0)

    async def get_chat_member(
        self, chat_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get chat member information"""
        data = {"chat_id": chat_id, "user_id": user_id}
        result = await self._request("getChatMember", data)
        return result["result"]

    async def leave_chat(self, chat_id: int) -> bool:
        """Leave a chat"""
        data = {"chat_id": chat_id}
        result = await self._request("leaveChat", data)
        return result.get("result", False)

    # =======================
    # Files
    # =======================

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file information"""
        data = {"file_id": file_id}
        result = await self._request("getFile", data)
        return result["result"]

    def get_file_url(self, file_path: str) -> str:
        """Get direct URL for file download"""
        return f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"

    async def download_file(self, file_path: str) -> bytes:
        """Download file content"""
        url = self.get_file_url(file_path)
        response = await self._client.get(url)
        response.raise_for_status()
        return response.content

    # =======================
    # Webhooks
    # =======================

    async def set_webhook(
        self,
        url: str,
        certificate: Optional[str] = None,
        max_connections: int = 40,
        allowed_updates: Optional[List[str]] = None,
        drop_pending_updates: bool = False,
        secret_token: Optional[str] = None,
    ) -> bool:
        """
        Set webhook URL

        Args:
            url: HTTPS URL to send updates
            certificate: Path to public key certificate
            max_connections: Max simultaneous connections
            allowed_updates: List of update types to receive
            drop_pending_updates: Drop all pending updates
            secret_token: Secret token for verification
        """
        data = {
            "url": url,
            "max_connections": max_connections,
            "drop_pending_updates": drop_pending_updates,
        }

        if allowed_updates:
            data["allowed_updates"] = allowed_updates
        if secret_token:
            data["secret_token"] = secret_token

        files = None
        if certificate:
            files = {"certificate": open(certificate, "rb")}

        result = await self._request("setWebhook", data, files)
        return result.get("result", False)

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """Delete webhook URL"""
        data = {"drop_pending_updates": drop_pending_updates}
        result = await self._request("deleteWebhook", data)
        return result.get("result", False)

    async def get_webhook_info(self) -> WebhookInfo:
        """Get current webhook status"""
        result = await self._request("getWebhookInfo")
        return WebhookInfo(**result["result"])


# =======================
# Keyboard Helpers
# =======================


def inline_keyboard(
    buttons: List[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Create inline keyboard markup

    Args:
        buttons: 2D array of button definitions

    Example:
        inline_keyboard([
            [{"text": "Option 1", "callback_data": "opt1"}],
            [{"text": "Option 2", "callback_data": "opt2"}, {"text": "URL", "url": "https://..."}],
        ])
    """
    return {"inline_keyboard": buttons}


def reply_keyboard(
    buttons: List[List[Dict[str, Any]]],
    resize_keyboard: bool = True,
    one_time_keyboard: bool = False,
    input_field_placeholder: Optional[str] = None,
    selective: bool = False,
) -> Dict[str, Any]:
    """
    Create reply keyboard markup

    Args:
        buttons: 2D array of button definitions
        resize_keyboard: Auto-resize keyboard
        one_time_keyboard: Hide after use
        input_field_placeholder: Placeholder text
        selective: Apply to specific user
    """
    return {
        "keyboard": buttons,
        "resize_keyboard": resize_keyboard,
        "one_time_keyboard": one_time_keyboard,
        "input_field_placeholder": input_field_placeholder,
        "selective": selective,
    }


def keyboard_button(
    text: str,
    request_user: Optional[Dict[str, Any]] = None,
    request_chat: Optional[Dict[str, Any]] = None,
    request_contact: bool = False,
    request_location: bool = False,
    request_poll: Optional[Dict[str, Any]] = None,
    web_app: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a keyboard button"""
    btn = {"text": text}

    if request_user:
        btn["request_user"] = request_user
    if request_chat:
        btn["request_chat"] = request_chat
    if request_contact:
        btn["request_contact"] = True
    if request_location:
        btn["request_location"] = True
    if request_poll:
        btn["request_poll"] = request_poll
    if web_app:
        btn["web_app"] = web_app

    return btn


def remove_keyboard(selective: bool = False) -> Dict[str, Any]:
    """Remove reply keyboard"""
    return {"remove_keyboard": True, "selective": selective}
