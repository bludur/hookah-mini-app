from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton
from hookah_core import services
from hookah_core.schemas import MixGenerateRequest
from bot.security import escape_md, CommandView
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Mix, Tobacco, User
from bot.database.utils import get_or_create_user
from bot.keyboards.menus import back_to_menu, confirm_delete_all_menu, favorites_menu, mix_menu, mix_rating_menu

router = Router()


def get_role_emoji(role: str) -> str:
    """Возвращает emoji для роли компонента."""
    roles = {
        "база": "🔵",
        "дополнение": "🟢",
        "акцент": "🟡",
    }
    return roles.get(role, "⚪")


@router.message(Command('mix'))
async def cmd_mix(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    await show_mix_menu(CommandView(message), session)


# ============ МЕНЮ МИКСОВ ============

@router.callback_query(F.data == "mix_menu")
async def show_mix_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает меню выбора типа микса."""
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

    if len(tobaccos) < 2:
        await callback.message.edit_text(
            "⚠️ *Мало табаков*\n\n"
            "Нужно минимум 2 для микса.\n"
            "Добавь ещё табаков в коллекцию!",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    else:
        await callback.message.edit_text(
            "🎨 *Подбор микса*\n\n"
            "Выбери способ:",
            parse_mode="Markdown",
            reply_markup=mix_menu(),
        )
    await callback.answer()


@router.callback_query(F.data == "mix_by_tobacco")
async def select_base_tobacco(callback: CallbackQuery, session: AsyncSession) -> None:
    """Выбор базового табака для микса."""
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .options(selectinload(Tobacco.category))
        .order_by(Tobacco.name)
        .limit(15)
    )
    tobaccos = result.scalars().all()

    # Создаём динамическую клавиатуру
    builder = InlineKeyboardBuilder()
    for tobacco in tobaccos:
        emoji = tobacco.category.emoji if tobacco.category else "🔸"
        builder.button(
            text=f"{emoji} {tobacco.name}",
            callback_data=f"mix_with:{tobacco.id}",
        )
    builder.adjust(1)

    # Кнопка назад
    builder.button(text="◀️ Назад", callback_data="mix_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        "🎯 *Выбери табак-основу:*",
        parse_mode="Markdown",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


# ============ ГЕНЕРАЦИЯ МИКСОВ ============

@router.callback_query(F.data.startswith("mix_with:"))
async def generate_mix_by_tobacco(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Генерирует микс на основе выбранного табака."""
    tobacco_id = int(callback.data.split(":")[1])

    # Показываем статус
    await callback.message.edit_text(
        "🔮 *Составляю микс...*",
        parse_mode="Markdown",
    )

    # Получаем выбранный табак
    result = await session.execute(
        select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user.has(User.telegram_id == callback.from_user.id))
    )
    base_tobacco = result.scalar_one_or_none()

    if not base_tobacco:
        await callback.message.edit_text(
            "❌ Табак не найден",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    # Сохраняем параметры для retry
    await state.update_data(
        request_type="base",
        base_tobacco=base_tobacco.name,
        taste_profile=None,
    )

    await _generate_mix(
        callback, session, state,
        request_type="base",
        base_tobacco=base_tobacco.name,
    )


@router.callback_query(F.data.startswith("mix_profile:"))
async def generate_mix_by_profile(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Генерирует микс по вкусовому профилю."""
    profile = callback.data.split(":")[1]

    # Показываем статус
    await callback.message.edit_text(
        "🔮 *Составляю микс...*",
        parse_mode="Markdown",
    )

    # Сохраняем параметры для retry
    await state.update_data(
        request_type="profile",
        base_tobacco=None,
        taste_profile=profile,
    )

    await _generate_mix(
        callback, session, state,
        request_type="profile",
        taste_profile=profile,
    )


@router.callback_query(F.data == "mix_surprise")
async def generate_surprise_mix(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Генерирует случайный микс."""
    # Показываем статус
    await callback.message.edit_text(
        "🔮 *Составляю микс...*",
        parse_mode="Markdown",
    )

    # Сохраняем параметры для retry
    await state.update_data(
        request_type="surprise",
        base_tobacco=None,
        taste_profile=None,
    )

    await _generate_mix(
        callback, session, state,
        request_type="surprise",
    )


@router.callback_query(F.data == "mix_retry")
async def retry_mix(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Повторяет генерацию микса."""
    data = await state.get_data()

    if not data.get("request_type"):
        await callback.message.edit_text(
            "🎨 *Подбор микса*\n\n"
            "Выбери способ:",
            parse_mode="Markdown",
            reply_markup=mix_menu(),
        )
        await callback.answer()
        return

    # Показываем статус
    await callback.message.edit_text(
        "🔮 *Составляю другой вариант...*",
        parse_mode="Markdown",
    )

    await _generate_mix(
        callback, session, state,
        request_type=data["request_type"],
        base_tobacco=data.get("base_tobacco"),
        taste_profile=data.get("taste_profile"),
    )


async def _generate_mix(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    request_type: str,
    base_tobacco: str = None,
    taste_profile: str = None,
) -> None:
    """Общая функция генерации микса."""
    await callback.answer()
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    data = MixGenerateRequest(request_type=request_type, base_tobacco=base_tobacco, taste_profile=taste_profile)
    mix, recommendation = await services.generate_mix(session, user, data)
    components_text = '\n'.join(
        f'{get_role_emoji(c.role)} {escape_md(c.tobacco)} — *{c.portion}%* ({c.role})'
        for c in recommendation.components)
    await callback.message.edit_text(
        f'🎨 *{escape_md(recommendation.name)}*\n\n📋 *Состав:*\n{components_text}\n\n'
        f'📝 {escape_md(recommendation.description)}\n\n💡 {escape_md(recommendation.tips)}',
        parse_mode='Markdown', reply_markup=mix_rating_menu(mix.id))


# ============ ОЦЕНКА И ИЗБРАННОЕ ============

@router.callback_query(F.data.startswith("rate_mix:"))
async def rate_mix(callback: CallbackQuery, session: AsyncSession) -> None:
    """Оценивает микс."""
    parts = callback.data.split(":")
    mix_id = int(parts[1])
    rating = int(parts[2])
    if rating not in (-1, 0, 1):
        await callback.answer("Недопустимая оценка", show_alert=True)
        return

    result = await session.execute(
        select(Mix).where(Mix.id == mix_id, Mix.user.has(User.telegram_id == callback.from_user.id))
    )
    mix = result.scalar_one_or_none()

    if not mix:
        await callback.answer("Микс не найден", show_alert=True)
        return
    if mix:
        mix.rating = rating
        await session.commit()

    if rating == 1:
        await callback.answer("👍 Оценка сохранена!")
    else:
        await callback.answer("👎 Учту!")


@router.callback_query(F.data.startswith("favorite_mix:"))
async def favorite_mix(callback: CallbackQuery, session: AsyncSession) -> None:
    """Добавляет/убирает микс из избранного."""
    mix_id = int(callback.data.split(":")[1])

    result = await session.execute(
        select(Mix).where(Mix.id == mix_id, Mix.user.has(User.telegram_id == callback.from_user.id))
    )
    mix = result.scalar_one_or_none()

    if mix:
        mix.is_favorite = not mix.is_favorite
        await session.commit()

        if mix.is_favorite:
            await callback.answer("⭐ Добавлено!")
        else:
            await callback.answer("Убрано из избранного")
    else:
        await callback.answer("Микс не найден", show_alert=True)


# ============ ИСТОРИЯ И ИЗБРАННОЕ ============

@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает историю миксов."""
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .order_by(Mix.created_at.desc())
        .limit(10)
    )
    mixes = result.scalars().all()

    if not mixes:
        await callback.message.edit_text(
            "📜 *История пуста*\n\n"
            "Здесь будут сохраняться миксы.",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    else:
        lines = []
        for mix in mixes:
            rating = ""
            if mix.rating == 1:
                rating = " 👍"
            elif mix.rating == -1:
                rating = " 👎"
            if mix.is_favorite:
                rating += " ⭐"
            lines.append(f"• {escape_md(mix.name)}{rating}")

        await callback.message.edit_text(
            "📜 *История миксов*\n\n" + "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    await callback.answer()


@router.callback_query((F.data == "favorites") | F.data.startswith("favorites_page:"))
async def show_favorites(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает избранные миксы."""
    page = max(0, int(callback.data.split(":")[1])) if ":" in callback.data else 0
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .where(Mix.is_favorite == True)
        .order_by(Mix.created_at.desc(), Mix.id.desc()).limit(6).offset(page * 5)
    )
    mixes = list(result.scalars().all())
    has_more = len(mixes) > 5
    mixes = mixes[:5]

    builder = InlineKeyboardBuilder.from_markup(favorites_menu(has_favorites=bool(mixes)))
    if page > 0:
        builder.row(InlineKeyboardButton(text='Назад', callback_data=f'favorites_page:{page - 1}'))
    if has_more:
        builder.row(InlineKeyboardButton(text='Далее', callback_data=f'favorites_page:{page + 1}'))
    if not mixes:
        await callback.message.edit_text(
            "⭐ *Избранное пусто*\n\n"
            "Добавляй понравившиеся миксы!",
            parse_mode="Markdown",
            reply_markup=favorites_menu(has_favorites=False),
        )
    else:
        text = "⭐ *Избранные миксы*\n\n"
        for mix in mixes:
            components = ", ".join(
                f"{escape_md(name)} {data['portion']}%"
                for name, data in mix.components.items()
            )
            text += f"🎨 *{escape_md(mix.name)}*\n{components}\n\n"

        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


@router.callback_query(F.data == "clear_favorites")
async def confirm_clear_favorites(callback: CallbackQuery) -> None:
    """Подтверждение очистки избранного."""
    await callback.message.edit_text(
        "⚠️ *Очистить избранное?*\n\n"
        "Все миксы будут убраны из избранного.\n"
        "(Сами миксы останутся в истории)",
        parse_mode="Markdown",
        reply_markup=confirm_delete_all_menu("clear_favorites"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_favorites")
async def clear_all_favorites(callback: CallbackQuery, session: AsyncSession) -> None:
    """Очищает все избранные миксы."""
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .where(Mix.is_favorite == True)
    )
    mixes = result.scalars().all()
    
    count = len(mixes)
    for mix in mixes:
        mix.is_favorite = False
    
    await session.commit()
    
    await callback.message.edit_text(
        f"✅ *Избранное очищено*\n\n"
        f"Убрано из избранного: {count} миксов",
        parse_mode="Markdown",
        reply_markup=back_to_menu(),
    )
    await callback.answer()
