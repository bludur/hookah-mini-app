"""Public app launcher. Never reads collection data or executes private commands."""
import hashlib
import hmac
import re
import logging
import asyncio
import aiohttp

from aiogram.types import Message
from hookah_core.config import settings
from hookah_core.errors import DomainError

logger = logging.getLogger(__name__)


async def send_launch_reply(reply):
    """Check Telegram's result; HTTP webhook acknowledgements alone cannot prove delivery."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as client:
            async with client.post(f'https://api.telegram.org/bot{settings.bot_token.get_secret_value()}/sendMessage', json=reply) as response:
                status = response.status
                result = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        logger.warning('Launcher delivery failed: network or invalid response')
        raise DomainError('Telegram temporarily unavailable', 503) from None
    if result.get('ok') is True:
        logger.info('Launcher message delivered')
        return
    code = result.get('error_code', status)
    # Never log request URLs, credentials, chat IDs or message text.
    reason = result.get('description', '')
    category = ('bot_removed' if 'kicked' in reason else
                'write_forbidden' if 'rights' in reason or 'CHAT_WRITE_FORBIDDEN' in reason else
                'topic_closed' if 'TOPIC_CLOSED' in reason else 'telegram_rejected')
    logger.warning('Launcher delivery rejected: code=%s category=%s', code, category)
    raise DomainError('Telegram rejected launcher message', 503)


def webhook_secret():
    return hmac.new(settings.bot_token.get_secret_value().encode(),
                    b'hookah:launcher-webhook:v1', hashlib.sha256).hexdigest()


def launch_reply(message: Message, username: str):
    if message.chat.type not in ('private', 'group', 'supergroup'):
        return None
    # Anonymous admins use a synthetic bot sender; this public action needs no user identity.
    if not message.sender_chat and (not message.from_user or message.from_user.is_bot):
        return None
    command = re.fullmatch(r'/app(?:@([A-Za-z0-9_]+))?\s*', message.text or '')
    if not command or (command[1] and command[1].lower() != username.lower()):
        return None
    if not any(entity.type == 'bot_command' and entity.offset == 0 for entity in message.entities or []):
        return None
    reply = {'chat_id': message.chat.id, 'text': '🌿 Коллекция табаков и миксы — в приложении. У каждого участника своя коллекция.',
             'reply_markup': {'inline_keyboard': [[{'text': '🌿 Открыть приложение', 'url': f'https://t.me/{username}?startapp'}]]}}
    if message.message_thread_id is not None:
        reply['message_thread_id'] = message.message_thread_id
    return reply
