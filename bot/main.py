import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
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
    await init_db()
    logger.info("Database initialized")

    # Создание бота и диспетчера
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.update.middleware(DatabaseMiddleware())

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(collection.router)
    dp.include_router(mix.router)

    # Команды
    await set_commands(bot)

    # Запуск
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started successfully!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
