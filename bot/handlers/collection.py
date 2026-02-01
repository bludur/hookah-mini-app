from aiogram import F, Router
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
    confirm_delete_menu,
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
        .where(Tobacco.id == tobacco_id)
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
        f"{emoji} *{tobacco.name}*\n\n"
        f"🏷 Бренд: {brand}\n"
        f"📁 Категория: {category_name}\n"
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


@router.message(AddTobaccoStates.waiting_name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Обрабатывает название табака."""
    name = message.text.strip()

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


@router.message(AddTobaccoStates.waiting_brand)
async def process_brand(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает бренд табака."""
    brand = message.text.strip()
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

    # Проверяем уникальность названия
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .where(Tobacco.name.ilike(name))
    )
    existing = result.scalar_one_or_none()

    if existing:
        await state.clear()
        await callback.message.edit_text(
            f"⚠️ *Табак «{name}» уже есть в коллекции!*",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        await callback.answer()
        return

    # Создаём табак
    tobacco = Tobacco(
        user_id=user.id,
        name=name,
        brand=brand,
        category_id=category_id,
    )
    session.add(tobacco)
    await session.commit()

    # Очищаем state
    await state.clear()

    brand_text = f"🏷 {brand}" if brand else ""
    await callback.message.edit_text(
        f"✅ *Табак добавлен!*\n\n"
        f"🟢 *{name}*\n"
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


@router.message(AddTobaccoStates.waiting_bulk)
async def process_bulk_tobaccos(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает список табаков."""
    lines = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    
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
    
    # Получаем существующие табаки пользователя для проверки дубликатов
    result = await session.execute(
        select(Tobacco.name).where(Tobacco.user_id == user.id)
    )
    existing_names = {name.lower() for name in result.scalars().all()}
    
    added = []
    skipped = []
    errors = []
    
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        name = parts[0] if parts else ""
        
        if len(name) < 2:
            errors.append(f"• `{line}` — слишком короткое название")
            continue
        
        # Проверяем дубликат
        if name.lower() in existing_names:
            skipped.append(f"• {name}")
            continue
        
        brand = parts[1] if len(parts) > 1 else None
        category_name = parts[2].lower() if len(parts) > 2 else None
        category_id = categories.get(category_name) if category_name else None
        
        tobacco = Tobacco(
            user_id=user.id,
            name=name,
            brand=brand,
            category_id=category_id,
        )
        session.add(tobacco)
        existing_names.add(name.lower())  # Добавляем в набор чтобы избежать дублей в одном списке
        added.append(f"• {name}" + (f" ({brand})" if brand else ""))
    
    await session.commit()
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
        select(Tobacco).where(Tobacco.id == tobacco_id)
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        await callback.answer("Табак не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"🗑 *Удалить табак?*\n\n"
        f"*{tobacco.name}*\n\n"
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
        select(Tobacco).where(Tobacco.id == tobacco_id)
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


# ============ РЕДАКТИРОВАНИЕ ТАБАКА ============

@router.callback_query(F.data.startswith("edit_tobacco:"))
async def edit_tobacco(callback: CallbackQuery) -> None:
    """Редактирование табака (заглушка)."""
    await callback.answer("🚧 Функция в разработке", show_alert=True)
