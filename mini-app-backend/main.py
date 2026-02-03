import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import init_db, get_session
from models import User, Category, Tobacco, Mix
from schemas import (
    UserCreate, UserResponse,
    CategoryResponse,
    TobaccoCreate, TobaccoBulkCreate, TobaccoUpdate, TobaccoResponse, TobaccoBulkResponse,
    MixResponse, MixGenerateRequest, MixGenerateResponse, MixComponent,
    MixRateRequest, MixFavoriteRequest,
    StatsResponse,
)
from llm_service import llm_service

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle управления приложением."""
    await init_db()
    logger.info("Application started")
    yield
    logger.info("Application stopped")


app = FastAPI(
    title="Hookah Mix Mini App API",
    description="API для Telegram Mini App управления коллекцией табаков и генерации миксов",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ HELPERS ============

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> User:
    """Получает или создаёт пользователя."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def get_current_user(
    x_telegram_user_id: int = Header(..., alias="X-Telegram-User-Id"),
    x_telegram_username: Optional[str] = Header(None, alias="X-Telegram-Username"),
    x_telegram_first_name: Optional[str] = Header(None, alias="X-Telegram-First-Name"),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency для получения текущего пользователя из заголовков."""
    # Декодируем URL-encoded значения (для поддержки кириллицы)
    username = unquote(x_telegram_username) if x_telegram_username else None
    first_name = unquote(x_telegram_first_name) if x_telegram_first_name else None
    
    return await get_or_create_user(
        session,
        telegram_id=x_telegram_user_id,
        username=username,
        first_name=first_name,
    )


# ============ USER ENDPOINTS ============

@app.get("/api/user/me", response_model=UserResponse, tags=["User"])
async def get_me(user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе."""
    return user


@app.get("/api/user/stats", response_model=StatsResponse, tags=["User"])
async def get_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить статистику пользователя."""
    # Количество табаков
    tobaccos_count = await session.scalar(
        select(func.count(Tobacco.id)).where(Tobacco.user_id == user.id)
    )

    # Количество миксов
    mixes_count = await session.scalar(
        select(func.count(Mix.id)).where(Mix.user_id == user.id)
    )

    # Количество избранных
    favorites_count = await session.scalar(
        select(func.count(Mix.id)).where(
            Mix.user_id == user.id,
            Mix.is_favorite == True
        )
    )

    return StatsResponse(
        tobaccos_count=tobaccos_count or 0,
        mixes_count=mixes_count or 0,
        favorites_count=favorites_count or 0,
    )


# ============ CATEGORY ENDPOINTS ============

@app.get("/api/categories", response_model=List[CategoryResponse], tags=["Categories"])
async def get_categories(session: AsyncSession = Depends(get_session)):
    """Получить все категории табаков."""
    result = await session.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


# ============ TOBACCO ENDPOINTS ============

@app.get("/api/tobaccos", response_model=List[TobaccoResponse], tags=["Tobaccos"])
async def get_tobaccos(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить все табаки пользователя."""
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .options(selectinload(Tobacco.category))
        .order_by(Tobacco.name)
    )
    return result.scalars().all()


@app.get("/api/tobaccos/{tobacco_id}", response_model=TobaccoResponse, tags=["Tobaccos"])
async def get_tobacco(
    tobacco_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить конкретный табак."""
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.id == tobacco_id, Tobacco.user_id == user.id)
        .options(selectinload(Tobacco.category))
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        raise HTTPException(status_code=404, detail="Табак не найден")

    return tobacco


@app.post("/api/tobaccos", response_model=TobaccoResponse, tags=["Tobaccos"])
async def create_tobacco(
    data: TobaccoCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Добавить табак в коллекцию."""
    # Проверяем уникальность названия
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .where(Tobacco.name.ilike(data.name))
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail=f"Табак '{data.name}' уже есть в коллекции")

    tobacco = Tobacco(
        user_id=user.id,
        name=data.name,
        brand=data.brand,
        category_id=data.category_id,
        notes=data.notes,
    )
    session.add(tobacco)
    await session.commit()
    await session.refresh(tobacco)

    # Загружаем категорию
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.id == tobacco.id)
        .options(selectinload(Tobacco.category))
    )
    return result.scalar_one()


@app.post("/api/tobaccos/bulk", response_model=TobaccoBulkResponse, tags=["Tobaccos"])
async def create_tobaccos_bulk(
    data: TobaccoBulkCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Массовое добавление табаков."""
    # Получаем существующие названия
    result = await session.execute(
        select(Tobacco.name).where(Tobacco.user_id == user.id)
    )
    existing_names = {name.lower() for name in result.scalars().all()}

    added = []
    skipped = []
    errors = []

    for item in data.tobaccos:
        if len(item.name) < 2:
            errors.append(f"'{item.name}' — слишком короткое название")
            continue

        if item.name.lower() in existing_names:
            skipped.append(item.name)
            continue

        tobacco = Tobacco(
            user_id=user.id,
            name=item.name,
            brand=item.brand,
            category_id=item.category_id,
        )
        session.add(tobacco)
        existing_names.add(item.name.lower())
        added.append(item.name)

    await session.commit()

    return TobaccoBulkResponse(added=added, skipped=skipped, errors=errors)


@app.put("/api/tobaccos/{tobacco_id}", response_model=TobaccoResponse, tags=["Tobaccos"])
async def update_tobacco(
    tobacco_id: int,
    data: TobaccoUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Обновить табак."""
    result = await session.execute(
        select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user_id == user.id)
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        raise HTTPException(status_code=404, detail="Табак не найден")

    if data.name is not None:
        tobacco.name = data.name
    if data.brand is not None:
        tobacco.brand = data.brand
    if data.category_id is not None:
        tobacco.category_id = data.category_id
    if data.notes is not None:
        tobacco.notes = data.notes

    await session.commit()
    await session.refresh(tobacco)

    # Загружаем категорию
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.id == tobacco.id)
        .options(selectinload(Tobacco.category))
    )
    return result.scalar_one()


@app.delete("/api/tobaccos/{tobacco_id}", tags=["Tobaccos"])
async def delete_tobacco(
    tobacco_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Удалить табак."""
    result = await session.execute(
        select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user_id == user.id)
    )
    tobacco = result.scalar_one_or_none()

    if not tobacco:
        raise HTTPException(status_code=404, detail="Табак не найден")

    await session.delete(tobacco)
    await session.commit()

    return {"message": "Табак удалён"}


@app.delete("/api/tobaccos", tags=["Tobaccos"])
async def delete_all_tobaccos(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Удалить все табаки пользователя."""
    result = await session.execute(
        select(Tobacco).where(Tobacco.user_id == user.id)
    )
    tobaccos = result.scalars().all()

    count = len(tobaccos)
    for tobacco in tobaccos:
        await session.delete(tobacco)

    await session.commit()

    return {"message": f"Удалено {count} табаков"}


# ============ MIX ENDPOINTS ============

@app.post("/api/mixes/generate", response_model=MixGenerateResponse, tags=["Mixes"])
async def generate_mix(
    data: MixGenerateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Сгенерировать микс через AI."""
    # Получаем табаки пользователя
    result = await session.execute(
        select(Tobacco)
        .where(Tobacco.user_id == user.id)
        .options(selectinload(Tobacco.category))
    )
    tobaccos = result.scalars().all()

    if len(tobaccos) < 2:
        raise HTTPException(status_code=400, detail="Нужно минимум 2 табака для микса")

    # Формируем данные для LLM
    tobaccos_data = [
        {
            "name": t.name,
            "brand": t.brand,
            "category": t.category.name if t.category else None,
        }
        for t in tobaccos
    ]

    # Получаем историю оценок
    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .where(Mix.rating.isnot(None))
    )
    rated_mixes = result.scalars().all()
    liked = [m.name for m in rated_mixes if m.rating == 1]
    disliked = [m.name for m in rated_mixes if m.rating == -1]

    # Получаем последние миксы для исключения повторений
    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .order_by(Mix.created_at.desc())
        .limit(10)
    )
    recent_mixes = result.scalars().all()
    previous_names = [m.name for m in recent_mixes]

    try:
        # Генерируем микс
        recommendation = await llm_service.generate_mix(
            tobaccos=tobaccos_data,
            request_type=data.request_type,
            base_tobacco=data.base_tobacco,
            taste_profile=data.taste_profile,
            liked_mixes=liked if liked else None,
            disliked_mixes=disliked if disliked else None,
            previous_mixes=previous_names if previous_names else None,
        )

        # Сохраняем микс в БД
        components_dict = {
            c.tobacco: {"portion": c.portion, "role": c.role}
            for c in recommendation.components
        }

        mix = Mix(
            user_id=user.id,
            name=recommendation.name,
            components=components_dict,
            description=recommendation.description,
            tips=recommendation.tips,
            request_type=data.request_type,
        )
        session.add(mix)
        await session.commit()
        await session.refresh(mix)

        return MixGenerateResponse(
            id=mix.id,
            name=recommendation.name,
            components=[
                MixComponent(
                    tobacco=c.tobacco,
                    portion=c.portion,
                    role=c.role,
                )
                for c in recommendation.components
            ],
            description=recommendation.description,
            tips=recommendation.tips,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mixes", response_model=List[MixResponse], tags=["Mixes"])
async def get_mixes(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
):
    """Получить историю миксов."""
    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .order_by(Mix.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@app.get("/api/mixes/favorites", response_model=List[MixResponse], tags=["Mixes"])
async def get_favorites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить избранные миксы."""
    result = await session.execute(
        select(Mix)
        .where(Mix.user_id == user.id)
        .where(Mix.is_favorite == True)
        .order_by(Mix.created_at.desc())
    )
    return result.scalars().all()


@app.get("/api/mixes/{mix_id}", response_model=MixResponse, tags=["Mixes"])
async def get_mix(
    mix_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить конкретный микс."""
    result = await session.execute(
        select(Mix).where(Mix.id == mix_id, Mix.user_id == user.id)
    )
    mix = result.scalar_one_or_none()

    if not mix:
        raise HTTPException(status_code=404, detail="Микс не найден")

    return mix


@app.post("/api/mixes/{mix_id}/rate", response_model=MixResponse, tags=["Mixes"])
async def rate_mix(
    mix_id: int,
    data: MixRateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Оценить микс."""
    result = await session.execute(
        select(Mix).where(Mix.id == mix_id, Mix.user_id == user.id)
    )
    mix = result.scalar_one_or_none()

    if not mix:
        raise HTTPException(status_code=404, detail="Микс не найден")

    mix.rating = data.rating
    await session.commit()
    await session.refresh(mix)

    return mix


@app.post("/api/mixes/{mix_id}/favorite", response_model=MixResponse, tags=["Mixes"])
async def toggle_favorite(
    mix_id: int,
    data: MixFavoriteRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Добавить/убрать из избранного."""
    result = await session.execute(
        select(Mix).where(Mix.id == mix_id, Mix.user_id == user.id)
    )
    mix = result.scalar_one_or_none()

    if not mix:
        raise HTTPException(status_code=404, detail="Микс не найден")

    mix.is_favorite = data.is_favorite
    await session.commit()
    await session.refresh(mix)

    return mix


@app.delete("/api/mixes/favorites", tags=["Mixes"])
async def clear_favorites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Очистить избранное."""
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

    return {"message": f"Убрано из избранного: {count} миксов"}


# ============ HEALTH CHECK ============

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
