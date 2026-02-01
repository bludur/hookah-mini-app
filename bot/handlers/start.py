from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Tobacco, User
from bot.database.utils import get_or_create_user
from bot.keyboards.menus import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Обработчик команды /start."""
    # Ищем пользователя по telegram_id
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    first_name = message.from_user.first_name or "друг"

    if not user:
        # Создаём нового пользователя
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(user)
        await session.commit()

        await message.answer(
            f"🎉 *Добро пожаловать, {first_name}!*\n\n"
            "Я — твой помощник по составлению миксов для кальяна.\n\n"
            "*Как это работает:*\n"
            "1️⃣ Добавь табаки из своей коллекции\n"
            "2️⃣ Попроси подобрать микс\n"
            "3️⃣ Оценивай — я запомню предпочтения!\n\n"
            "Начнём? 👇",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
    else:
        # Считаем количество табаков
        result = await session.execute(
            select(Tobacco).where(Tobacco.user_id == user.id)
        )
        tobaccos = result.scalars().all()
        count = len(tobaccos)

        await message.answer(
            f"👋 *С возвращением, {first_name}!*\n\n"
            f"📦 В коллекции: *{count}* табаков\n\n"
            "Что делаем?",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает главное меню."""
    # Получаем или создаём пользователя
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    result = await session.execute(
        select(Tobacco).where(Tobacco.user_id == user.id)
    )
    tobaccos = result.scalars().all()
    count = len(tobaccos)

    await callback.message.edit_text(
        "🏠 *Главное меню*\n\n"
        f"📦 Табаков: *{count}*",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    """Пустой callback для неактивных кнопок."""
    await callback.answer()
