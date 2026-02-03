import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Base, Category

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Создаёт таблицы и заполняет начальные данные."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await init_categories()
    logger.info("Database initialized")


async def init_categories() -> None:
    """Создаёт категории табаков если их нет."""
    categories_data = [
        ("Ягодные", "🍓", "сладкий"),
        ("Цитрусовые", "🍊", "кислый"),
        ("Фруктовые", "🍎", "сладкий"),
        ("Тропические", "🥭", "сладкий"),
        ("Мятные", "🍃", "свежий"),
        ("Холодок", "❄️", "свежий"),
        ("Десертные", "🍬", "сладкий"),
        ("Напитки", "🥤", "разный"),
        ("Цветочные", "🌸", "нейтральный"),
        ("Пряные", "🌶", "терпкий"),
    ]

    async with async_session() as session:
        # Проверяем есть ли уже категории
        result = await session.execute(select(Category).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        # Добавляем все категории
        for name, emoji, taste_profile in categories_data:
            category = Category(
                name=name,
                emoji=emoji,
                taste_profile=taste_profile,
            )
            session.add(category)

        await session.commit()
        logger.info("Categories initialized")


async def get_session():
    """Dependency для получения сессии БД."""
    async with async_session() as session:
        yield session
