from typing import Any, List

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Моя коллекция", callback_data="collection")
    builder.button(text="➕ Добавить табак", callback_data="add_tobacco")
    builder.button(text="📋 Добавить список", callback_data="add_tobacco_bulk")
    builder.button(text="🎨 Подобрать микс", callback_data="mix_menu")
    builder.button(text="📜 История", callback_data="history")
    builder.button(text="⭐ Избранное", callback_data="favorites")
    builder.adjust(2, 1, 1, 2)
    return builder.as_markup()


def mix_menu() -> InlineKeyboardMarkup:
    """Меню выбора типа микса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 На основе табака", callback_data="mix_by_tobacco")
    builder.button(text="🍬 Сладкий", callback_data="mix_profile:сладкий")
    builder.button(text="🍋 Кислый", callback_data="mix_profile:кислый")
    builder.button(text="🌿 Свежий", callback_data="mix_profile:свежий")
    builder.button(text="🎲 Удиви меня", callback_data="mix_surprise")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()


def collection_menu(
    tobaccos: List[Any], page: int = 0, page_size: int = 8
) -> InlineKeyboardMarkup:
    """Меню коллекции табаков с пагинацией."""
    builder = InlineKeyboardBuilder()

    # Вычисляем пагинацию
    total_pages = max(1, (len(tobaccos) + page_size - 1) // page_size)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(tobaccos))
    page_tobaccos = tobaccos[start_idx:end_idx]

    # Кнопки табаков
    for tobacco in page_tobaccos:
        emoji = tobacco.category.emoji if tobacco.category else "🔸"
        brand = f" • {tobacco.brand}" if tobacco.brand else ""
        text = f"{emoji} {tobacco.name}{brand}"
        builder.button(text=text, callback_data=f"tobacco:{tobacco.id}")

    # Размещаем табаки по 1 в ряд
    builder.adjust(1)

    # Пагинация (если больше 1 страницы)
    if total_pages > 1:
        pagination = InlineKeyboardBuilder()
        if page > 0:
            pagination.button(text="◀️", callback_data=f"collection_page:{page - 1}")
        pagination.button(text=f"{page + 1}/{total_pages}", callback_data="noop")
        if page < total_pages - 1:
            pagination.button(text="▶️", callback_data=f"collection_page:{page + 1}")
        pagination.adjust(3)
        builder.attach(pagination)

    # Нижние кнопки
    bottom = InlineKeyboardBuilder()
    bottom.button(text="➕ Добавить", callback_data="add_tobacco")
    bottom.button(text="◀️ Меню", callback_data="main_menu")
    bottom.adjust(2)
    builder.attach(bottom)

    return builder.as_markup()


def tobacco_detail_menu(tobacco_id: int) -> InlineKeyboardMarkup:
    """Меню детальной информации о табаке."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎨 Микс с ним", callback_data=f"mix_with:{tobacco_id}")
    builder.button(text="✏️ Изменить", callback_data=f"edit_tobacco:{tobacco_id}")
    builder.button(text="🗑 Удалить", callback_data=f"delete_tobacco:{tobacco_id}")
    builder.button(text="◀️ К коллекции", callback_data="collection")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def categories_menu(categories: List[Any]) -> InlineKeyboardMarkup:
    """Меню выбора категории табака."""
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.button(
            text=f"{category.emoji} {category.name}",
            callback_data=f"category:{category.id}",
        )

    # Категории по 2 в ряд
    builder.adjust(2)

    # Кнопки действий
    bottom = InlineKeyboardBuilder()
    bottom.button(text="⏭ Пропустить", callback_data="category:skip")
    bottom.button(text="❌ Отмена", callback_data="main_menu")
    bottom.adjust(1)
    builder.attach(bottom)

    return builder.as_markup()


def mix_rating_menu(mix_id: int) -> InlineKeyboardMarkup:
    """Меню оценки микса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👍", callback_data=f"rate_mix:{mix_id}:1")
    builder.button(text="👎", callback_data=f"rate_mix:{mix_id}:-1")
    builder.button(text="⭐ В избранное", callback_data=f"favorite_mix:{mix_id}")
    builder.button(text="🔄 Другой вариант", callback_data="mix_retry")
    builder.button(text="◀️ Меню", callback_data="main_menu")
    builder.adjust(3, 2)
    return builder.as_markup()


def confirm_delete_menu(tobacco_id: int) -> InlineKeyboardMarkup:
    """Меню подтверждения удаления табака."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_delete:{tobacco_id}")
    builder.button(text="❌ Отмена", callback_data=f"tobacco:{tobacco_id}")
    builder.adjust(2)
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Главное меню", callback_data="main_menu")
    return builder.as_markup()


def skip_brand_menu() -> InlineKeyboardMarkup:
    """Меню пропуска бренда при добавлении табака."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip_brand")
    builder.button(text="❌ Отмена", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()
