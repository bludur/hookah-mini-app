"""Public app launcher. Never reads collection data or executes private commands."""
import hashlib
import hmac
import re

from aiogram.types import Message
from hookah_core.config import settings


def webhook_secret():
    return hmac.new(settings.bot_token.get_secret_value().encode(),
                    b'hookah:launcher-webhook:v1', hashlib.sha256).hexdigest()


def launch_reply(message: Message, username: str):
    if message.chat.type not in ('private', 'group', 'supergroup') or not message.from_user or message.from_user.is_bot:
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
