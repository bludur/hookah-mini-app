import logging
import re
from types import SimpleNamespace

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from pydantic import ValidationError

from hookah_core.errors import DomainError

logger = logging.getLogger(__name__)


def escape_md(value):
    return re.sub(r'([\\_*`\[])', r'\\\1', str(value))


class CommandView:
    """Adapt a command to the same menu renderer used by inline callbacks."""
    def __init__(self, message, data=''):
        self.from_user = message.from_user
        self.data = data
        self.message = SimpleNamespace(edit_text=message.answer)

    async def answer(self, *args, **kwargs):
        pass


class PrivateChatMiddleware(BaseMiddleware):
    async def reply_error(self, event, message):
        if isinstance(event, CallbackQuery):
            try:
                await event.answer(message, show_alert=True)
            except TelegramBadRequest:
                # A provider request may outlive Telegram's callback-query lifetime.
                await event.message.answer(message)
        else:
            await event.answer(message)

    async def __call__(self, handler, event, data):
        # Handle the public launcher here; never let group messages reach private handlers.
        if isinstance(event, Message) and (event.text or '').startswith('/app'):
            from bot.launcher import launch_reply
            from aiogram.types import InlineKeyboardMarkup
            bot = data.get('bot') or event.bot
            username = (await bot.me()).username
            reply = launch_reply(event, username)
            if reply:
                reply['reply_markup'] = InlineKeyboardMarkup.model_validate(reply['reply_markup'])
                return await bot.send_message(**reply)
        message = event.message if isinstance(event, CallbackQuery) else event
        if not isinstance(message, Message) or message.chat.type != 'private':
            if isinstance(event, CallbackQuery):
                await event.answer('Откройте личный чат с ботом.', show_alert=True)
            return
        try:
            return await handler(event, data)
        except DomainError as exc:
            await data['session'].rollback()
            await self.reply_error(event, str(exc))
        except (ValidationError, ValueError, KeyError, IndexError):
            await data['session'].rollback()
            await self.reply_error(event, 'Проверьте данные или откройте меню заново через /start.')
        except Exception as exc:
            await data['session'].rollback()
            logger.error('Bot handler failed (%s)', type(exc).__name__)
            await self.reply_error(event, 'Не удалось выполнить действие. Попробуйте позже.')
