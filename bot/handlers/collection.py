from aiogram import F, Router
from aiogram.filters import Command
from hookah_core import services
from hookah_core.schemas import TobaccoCreate, TobaccoUpdate
from hookah_core.errors import DomainError
from bot.security import escape_md, CommandView
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import Category, Tobacco, User
from bot.database.utils import get_or_create_user
from bot.keyboards.menus import (
    back_to_menu,
    categories_menu,
    collection_menu,
    confirm_delete_all_menu,
    confirm_delete_menu,
    delete_collection_menu,
    skip_brand_menu,
    tobacco_detail_menu,
)

router = Router()


class AddTobaccoStates(StatesGroup):
    """Состояния для добавления табака."""
    waiting_name = State()
    waiting_brand = State()
    waiting_category = State()
    waiting_bulk = State()  # Для массового добавления


class DeleteTobaccoStates(StatesGroup):
    """Состояния для удаления табаков."""
    selecting = State()  # Выбор табаков для удаления


@router.message(Command('collection'))
async def cmd_collection(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    await show_collection(CommandView(message), session)


@router.message(Command('add'))
async def cmd_add(message: Message, state: FSMContext):
    await state.clear()
    await start_add_tobacco(CommandView(message), state)


# ============ ПРОСМОТР КОЛЛЕКЦИИ ============

@router.callback_query(F.data == "collection")
async def show_collection(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает коллекцию табаков."""
    # Получаем или создаём пользователя
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    # Получаем табаки с категориями
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .options(selectinload(Tobacco.category))
        .order_by(Tobacco.name)
    )
    tobaccos = result.scalars().all()

    if not tobaccos:
        await callback.message.edit_text(
            "📦 *Коллекция пуста*\n\n"
            "Добавь табаки!",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    else:
        await callback.message.edit_text(
            f"📦 *Твоя коллекция* ({len(tobaccos)} шт.)\n\n"
            "Нажми на табак:",
            parse_mode="Markdown",
            reply_markup=collection_menu(list(tobaccos)),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("collection_page:"))
async def collection_page(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключение страницы коллекции."""
    page = int(callback.data.split(":")[1])

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
    )
    tobaccos = result.scalars().all()

    await callback.message.edit_reply_markup(
        reply_markup=collection_menu(list(tobaccos), page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tobacco:"))
async def show_tobacco(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показывает информацию о табаке."""
    tobacco_id = int(callback.data.split(":")[1])

    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.id == tobacco_id, Tobacco.user.has(User.telegram_id == callback.from_user.id))
        .options(selectinload(Tobacco.category))
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        await callback.answer("Табак не найден", show_alert=True)
        return

    emoji = tobacco.category.emoji if tobacco.category else "🔸"
    category_name = tobacco.category.name if tobacco.category else "Не указана"
    brand = tobacco.brand or "Не указан"
    date = tobacco.created_at.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"{emoji} *{escape_md(tobacco.name)}*\n\n"
        f"🏷 Бренд: {escape_md(brand)}\n"
        f"📁 Категория: {escape_md(category_name)}\n"
        f"📅 Добавлен: {date}",
        parse_mode="Markdown",
        reply_markup=tobacco_detail_menu(tobacco_id),
    )
    await callback.answer()


# ============ ДОБАВЛЕНИЕ ТАБАКА ============

@router.callback_query(F.data == "add_tobacco")
async def start_add_tobacco(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс добавления табака."""
    await state.set_state(AddTobaccoStates.waiting_name)
    await callback.message.edit_text(
        "➕ *Добавление табака*\n\n"
        "Введи название:",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), AddTobaccoStates.waiting_name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Обрабатывает название табака."""
    name = (message.text or "").strip()

    # Валидация
    if len(name) < 2 or len(name) > 100:
        await message.answer(
            "⚠️ Название должно быть от 2 до 100 символов.\n"
            "Попробуй ещё раз:"
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddTobaccoStates.waiting_brand)
    await message.answer(
        "🏷 *Укажи бренд табака:*\n\n"
        "Популярные бренды:\n"
        "• Darkside, Tangiers, Fumari\n"
        "• Must Have, Daily Hookah\n"
        "• Element, Burn, Spectrum\n"
        "• DarkSide, Duft, Chabacco\n\n"
        "_Напиши название или нажми «Пропустить»_",
        parse_mode="Markdown",
        reply_markup=skip_brand_menu(),
    )


@router.callback_query(F.data == "skip_brand", AddTobaccoStates.waiting_brand)
async def skip_brand(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Пропускает ввод бренда."""
    await state.update_data(brand=None)
    await state.set_state(AddTobaccoStates.waiting_category)

    # Получаем категории
    result = await session.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    await callback.message.edit_text(
        "📁 *Выбери категорию вкуса:*\n\n"
        "_Категория поможет AI лучше\nподбирать сочетания_",
        parse_mode="Markdown",
        reply_markup=categories_menu(list(categories)),
    )
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), AddTobaccoStates.waiting_brand)
async def process_brand(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает бренд табака."""
    brand = (message.text or "").strip()
    if len(brand) > 100:
        await message.answer("Бренд должен быть не длиннее 100 символов.")
        return
    await state.update_data(brand=brand)
    await state.set_state(AddTobaccoStates.waiting_category)

    # Получаем категории
    result = await session.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    await message.answer(
        "📁 *Выбери категорию вкуса:*\n\n"
        "_Категория поможет AI лучше\nподбирать сочетания_",
        parse_mode="Markdown",
        reply_markup=categories_menu(list(categories)),
    )


@router.callback_query(F.data.startswith("category:"), AddTobaccoStates.waiting_category)
async def process_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает выбор категории и сохраняет табак."""
    category_data = callback.data.split(":")[1]

    category_id = None if category_data == "skip" else int(category_data)

    # Получаем данные из state
    data = await state.get_data()
    name = data["name"]
    brand = data.get("brand")

    # Получаем или создаём пользователя
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )

    await services.create_tobacco(session, user.id, TobaccoCreate(
        name=name, brand=brand, category_id=category_id))

    # Очищаем state
    await state.clear()

    brand_text = f"🏷 {escape_md(brand)}" if brand else ""
    await callback.message.edit_text(
        f"✅ *Табак добавлен!*\n\n"
        f"🟢 *{escape_md(name)}*\n"
        f"{brand_text}",
        parse_mode="Markdown",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


# ============ МАССОВОЕ ДОБАВЛЕНИЕ ============

@router.callback_query(F.data == "add_tobacco_bulk")
async def start_add_tobacco_bulk(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает массовое добавление табаков."""
    await state.set_state(AddTobaccoStates.waiting_bulk)
    await callback.message.edit_text(
        "📋 *Массовое добавление табаков*\n\n"
        "Отправь список табаков, каждый с новой строки.\n\n"
        "*Форматы:*\n"
        "• `Название` — только название\n"
        "• `Название | Бренд` — с брендом\n"
        "• `Название | Бренд | Категория` — полный формат\n\n"
        "*Пример:*\n"
        "```\n"
        "Манго | Darkside\n"
        "Мята\n"
        "Клубника | Fumari | Ягодные\n"
        "Виноград | Tangiers\n"
        "```",
        parse_mode="Markdown",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), AddTobaccoStates.waiting_bulk)
async def process_bulk_tobaccos(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает список табаков."""
    lines = [line.strip() for line in (message.text or "").strip().split("\n") if line.strip()]
    
    if not lines:
        await message.answer(
            "⚠️ Список пуст. Отправь табаки, каждый с новой строки.",
            reply_markup=back_to_menu(),
        )
        return
    
    # Получаем или создаём пользователя
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    
    # Получаем категории для сопоставления
    result = await session.execute(select(Category))
    categories = {c.name.lower(): c.id for c in result.scalars().all()}
    
    rows = []
    for line in lines:
        parts = [part.strip() for part in line.split('|')]
        category_id = None
        if len(parts) > 2 and parts[2]:
            category_id = categories.get(parts[2].lower(), -1)
        rows.append({'name': parts[0], 'brand': parts[1] if len(parts) > 1 else None,
                     'category_id': category_id})
    result = await services.bulk_tobaccos(session, user.id, rows)
    added = [escape_md(name) for name in result['added']]
    skipped = [escape_md(name) for name in result['skipped']]
    errors = result['errors']
    await state.clear()
    
    # Формируем ответ
    text = f"✅ *Добавлено табаков: {len(added)}*\n\n"
    if added:
        text += "\n".join(added[:15])  # Показываем максимум 15
        if len(added) > 15:
            text += f"\n_...и ещё {len(added) - 15}_"
    
    if skipped:
        text += f"\n\n⏭ *Пропущено (уже есть): {len(skipped)}*\n" + "\n".join(skipped[:5])
        if len(skipped) > 5:
            text += f"\n_...и ещё {len(skipped) - 5}_"
    
    if errors:
        text += f"\n\n⚠️ *Ошибки ({len(errors)}):*\n" + "\n".join(errors[:5])
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu(),
    )


# ============ УДАЛЕНИЕ ТАБАКА ============

@router.callback_query(F.data.startswith("delete_tobacco:"))
async def confirm_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    """Запрашивает подтверждение удаления."""
    tobacco_id = int(callback.data.split(":")[1])

    result = await session.execute(
        select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user.has(User.telegram_id == callback.from_user.id))
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        await callback.answer("Табак не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 *Удалить табак?*\n\n"
        f"*{escape_md(tobacco.name)}*\n\n"
        "Это нельзя отменить.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_menu(tobacco_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_tobacco(callback: CallbackQuery, session: AsyncSession) -> None:
    """Удаляет табак."""
    tobacco_id = int(callback.data.split(":")[1])

    result = await session.execute(
        select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user.has(User.telegram_id == callback.from_user.id))
    )
    tobacco = result.scalar_one_or_none()

    if tobacco:
        await session.delete(tobacco)
        await session.commit()

    await callback.answer("✅ Удалено!")

    # Показываем коллекцию
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
    )
    tobaccos = result.scalars().all()

    if not tobaccos:
        await callback.message.edit_text(
            "📦 *Коллекция пуста*\n\n"
            "Добавь табаки!",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    else:
        await callback.message.edit_text(
            f"📦 *Твоя коллекция* ({len(tobaccos)} шт.)\n\n"
            "Нажми на табак:",
            parse_mode="Markdown",
            reply_markup=collection_menu(list(tobaccos)),
        )


# ============ МАССОВОЕ УДАЛЕНИЕ ============

@router.callback_query(F.data == "delete_mode")
async def start_delete_mode(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Начинает режим удаления табаков."""
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
    )
    tobaccos = result.scalars().all()

    if not tobaccos:
        await callback.answer("Коллекция пуста", show_alert=True)
        return

    await state.set_state(DeleteTobaccoStates.selecting)
    await state.update_data(selected=[], page=0)

    await callback.message.edit_text(
        "🗑 *Режим удаления*\n\n"
        "Выбери табаки для удаления\n"
        "(нажми чтобы выбрать/снять):",
        parse_mode="Markdown",
        reply_markup=delete_collection_menu(list(tobaccos)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_delete:"), DeleteTobaccoStates.selecting)
async def toggle_delete_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Переключает выбор табака для удаления."""
    tobacco_id = int(callback.data.split(":")[1])
    exists = await session.scalar(select(Tobacco.id).where(
        Tobacco.id == tobacco_id, Tobacco.user.has(User.telegram_id == callback.from_user.id)))
    if exists is None:
        raise DomainError('Табак не найден', 404)

    
    data = await state.get_data()
    selected = set(data.get("selected", []))
    page = data.get("page", 0)
    
    if tobacco_id in selected:
        selected.discard(tobacco_id)
    else:
        selected.add(tobacco_id)
    
    await state.update_data(selected=list(selected))
    
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
    )
    tobaccos = result.scalars().all()

    await callback.message.edit_reply_markup(
        reply_markup=delete_collection_menu(list(tobaccos), selected, page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_page:"), DeleteTobaccoStates.selecting)
async def delete_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Переключает страницу в режиме удаления."""
    page = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    selected = set(data.get("selected", []))
    await state.update_data(page=page)
    
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
    )
    tobaccos = result.scalars().all()

    await callback.message.edit_reply_markup(
        reply_markup=delete_collection_menu(list(tobaccos), selected, page)
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_selected", DeleteTobaccoStates.selecting)
async def delete_selected_tobaccos(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Удаляет выбранные табаки."""
    data = await state.get_data()
    selected = data.get("selected", [])
    
    if not selected:
        await callback.answer("Ничего не выбрано", show_alert=True)
        return
    
    # Удаляем выбранные табаки
    result = await session.execute(
        select(Tobacco).where(Tobacco.id.in_(selected), Tobacco.user.has(User.telegram_id == callback.from_user.id))
    )
    tobaccos_to_delete = result.scalars().all()
    
    count = len(tobaccos_to_delete)
    for tobacco in tobaccos_to_delete:
        await session.delete(tobacco)
    
    await session.commit()
    await state.clear()
    
    await callback.answer(f"✅ Удалено: {count} табаков")
    
    # Возвращаемся в коллекцию
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
    )
    tobaccos = result.scalars().all()

    if not tobaccos:
        await callback.message.edit_text(
            "📦 *Коллекция пуста*\n\n"
            "Добавь табаки!",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
    else:
        await callback.message.edit_text(
            f"📦 *Твоя коллекция* ({len(tobaccos)} шт.)\n\n"
            "Нажми на табак:",
            parse_mode="Markdown",
            reply_markup=collection_menu(list(tobaccos)),
        )


@router.callback_query(F.data == "delete_all_tobaccos")
async def confirm_delete_all_tobaccos(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение удаления всех табаков."""
    await state.clear()
    await callback.message.edit_text(
        "⚠️ *Удалить ВСЕ табаки?*\n\n"
        "Это действие нельзя отменить!\n"
        "Все табаки будут удалены из коллекции.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_all_menu("delete_all"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_all")
async def delete_all_tobaccos(callback: CallbackQuery, session: AsyncSession) -> None:
    """Удаляет все табаки пользователя."""
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
    for tobacco in tobaccos:
        await session.delete(tobacco)
    
    await session.commit()
    
    await callback.message.edit_text(
        f"✅ *Удалено: {count} табаков*\n\n"
        "Коллекция очищена.",
        parse_mode="Markdown",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


# ============ РЕДАКТИРОВАНИЕ ТАБАКА ============

class EditTobaccoStates(StatesGroup):
    waiting_fields = State()


@router.callback_query(F.data.startswith("edit_tobacco:"))
async def edit_tobacco(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    tobacco_id = int(callback.data.split(':')[1])
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    await services.load_tobacco(session, user.id, tobacco_id)
    await state.set_state(EditTobaccoStates.waiting_fields)
    await state.update_data(tobacco_id=tobacco_id)
    await callback.message.edit_text('Введите новое название и бренд: Название | Бренд. Пустой бренд после | очищает поле. Для отмены /start.')
    await callback.answer()


@router.message(F.text, ~F.text.startswith("/"), EditTobaccoStates.waiting_fields)
async def save_tobacco_edit(message: Message, state: FSMContext, session: AsyncSession):
    values = (message.text or '').split('|', 1)
    fields = {'name': values[0].strip()}
    if len(values) == 2:
        fields['brand'] = values[1].strip() or None
    data = await state.get_data()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
    await services.update_tobacco(session, user.id, data['tobacco_id'], TobaccoUpdate.model_validate(fields))
    await state.clear()
    await message.answer('Табак обновлён.', reply_markup=back_to_menu())
