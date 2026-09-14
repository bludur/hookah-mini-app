import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from bot.security import PrivateChatMiddleware
from hookah_core.database import engine
from hookah_core.limits import limiter
from hookah_core.llm import llm_service
from aiogram.types import BotCommand, TelegramObject
from aiogram import BaseMiddleware

from bot.config import settings
from bot.database.db import async_session, init_db
from bot.handlers import collection, mix, start

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для инъекции сессии БД в handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


async def set_commands(bot: Bot) -> None:
    """Устанавливает команды бота."""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="collection", description="📦 Моя коллекция"),
        BotCommand(command="add", description="➕ Добавить табак"),
        BotCommand(command="mix", description="🎨 Подобрать микс"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    """Главная функция запуска бота."""
    logger.info("Starting bot...")

    # Инициализация БД
    settings.validate_runtime()
    await init_db()
    await limiter.start()
    logger.info("Database initialized")

    # Создание бота и диспетчера
    bot = Bot(token=settings.bot_token.get_secret_value())
    storage = RedisStorage.from_url(
        settings.redis_url.get_secret_value(), state_ttl=3600, data_ttl=3600,
        key_builder=DefaultKeyBuilder(prefix=f'fsm:{settings.app_env}', with_bot_id=True),
    ) if settings.redis_url.get_secret_value() else MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.update.middleware(DatabaseMiddleware())
    dp.message.outer_middleware(PrivateChatMiddleware())
    dp.callback_query.outer_middleware(PrivateChatMiddleware())

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(collection.router)
    dp.include_router(mix.router)

    try:
        await set_commands(bot)
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Bot started successfully!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await storage.close()
        await llm_service.close()
        await limiter.close()
        await engine.dispose()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
