from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from bot.security import escape_md
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Tobacco, User
from bot.database.utils import get_or_create_user
from bot.keyboards.menus import main_menu

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(f'Привет, {escape_md(message.from_user.first_name)}! Добавь табаки и выбери микс.',
                         parse_mode='Markdown', reply_markup=main_menu())


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Показывает главное меню."""
    await state.clear()
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
