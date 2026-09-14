from pydantic import ValidationError
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .config import settings
from .database import dialect_insert
from .errors import DomainError, GenerationUnavailable
from .limits import limiter
from .llm import llm_service
from .models import User, Category, Tobacco, Mix
from .schemas import TobaccoCreate, TobaccoUpdate, MixGenerateRequest, MixRecommendation, normalized_name


async def get_or_create_user(session, telegram_id, username=None, first_name=None):
    stmt = dialect_insert(session, User).values(telegram_id=telegram_id, username=username, first_name=first_name)
    await session.execute(stmt.on_conflict_do_update(index_elements=['telegram_id'], set_={'username': username, 'first_name': first_name}))
    await session.commit()
    return (await session.execute(select(User).where(User.telegram_id == telegram_id).execution_options(populate_existing=True))).scalar_one()


async def lock_collection(session, user_id):
    # A row write serializes capacity checks on PostgreSQL and SQLite alike.
    await session.execute(update(User).where(User.id == user_id).values(id=user_id))


async def validate_category(session, category_id):
    if category_id is not None and await session.get(Category, category_id) is None:
        raise DomainError('Категория не найдена', 422)


async def commit_collection(session):
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise DomainError('Такой табак уже существует или данные изменились. Обновите коллекцию.', 409) from None


async def load_tobacco(session, user_id, tobacco_id):
    item = (await session.execute(select(Tobacco).where(Tobacco.id == tobacco_id, Tobacco.user_id == user_id)
                                  .options(selectinload(Tobacco.category)).execution_options(populate_existing=True))).scalar_one_or_none()
    if item is None:
        raise DomainError('Табак не найден', 404)
    return item


async def create_tobacco(session, user_id, data: TobaccoCreate):
    await lock_collection(session, user_id)
    await validate_category(session, data.category_id)
    count = await session.scalar(select(func.count(Tobacco.id)).where(Tobacco.user_id == user_id))
    if count >= settings.max_collection_size:
        raise DomainError(f'В коллекции может быть не более {settings.max_collection_size} табаков', 409)
    item = Tobacco(user_id=user_id, **data.model_dump())
    session.add(item)
    await commit_collection(session)
    return await load_tobacco(session, user_id, item.id)


async def update_tobacco(session, user_id, tobacco_id, data: TobaccoUpdate):
    await lock_collection(session, user_id)
    item = await load_tobacco(session, user_id, tobacco_id)
    values = data.model_dump(exclude_unset=True)
    if 'category_id' in values:
        await validate_category(session, values['category_id'])
    for key, value in values.items():
        setattr(item, key, value)
    await commit_collection(session)
    return await load_tobacco(session, user_id, tobacco_id)


async def bulk_tobaccos(session, user_id, rows):
    if not 1 <= len(rows) <= 100:
        raise DomainError('Добавляйте от 1 до 100 табаков за раз', 422)
    await lock_collection(session, user_id)
    names = set((await session.scalars(select(Tobacco.normalized_name).where(Tobacco.user_id == user_id))).all())
    categories = set((await session.scalars(select(Category.id))).all())
    result = {'added': [], 'skipped': [], 'errors': []}
    for number, row in enumerate(rows, 1):
        try:
            data = TobaccoCreate.model_validate(row)
        except ValidationError:
            result['errors'].append(f'Строка {number}: проверьте название и длину полей')
            continue
        if data.category_id is not None and data.category_id not in categories:
            result['errors'].append(f'Строка {number}: категория не найдена')
        elif normalized_name(data.name) in names:
            result['skipped'].append(data.name)
        elif len(names) >= settings.max_collection_size:
            result['errors'].append(f'Строка {number}: коллекция заполнена')
        else:
            session.add(Tobacco(user_id=user_id, **data.model_dump()))
            names.add(normalized_name(data.name))
            result['added'].append(data.name)
    await commit_collection(session)
    return result


async def generate_mix(session, user, data: MixGenerateRequest):
    user_id, telegram_id = user.id, user.telegram_id
    tobaccos = (await session.scalars(select(Tobacco).where(Tobacco.user_id == user_id)
                                     .options(selectinload(Tobacco.category))
                                     .order_by(Tobacco.id).limit(settings.max_collection_size + 1))).all()
    if not 2 <= len(tobaccos) <= settings.max_collection_size:
        raise DomainError(f'Для микса нужно от 2 до {settings.max_collection_size} табаков')
    names = {t.name for t in tobaccos}
    if data.base_tobacco and data.base_tobacco not in names:
        raise DomainError('Выбранный табак отсутствует в коллекции', 422)
    collection = [{'name': t.name, 'brand': (t.brand or '')[:100], 'category': t.category.name if t.category else None} for t in tobaccos]
    rated = (await session.scalars(select(Mix).where(Mix.user_id == user_id, Mix.rating.isnot(None))
                                  .order_by(Mix.created_at.desc(), Mix.id.desc()).limit(40))).all()
    recent = (await session.scalars(select(Mix.name).where(Mix.user_id == user_id)
                                   .order_by(Mix.created_at.desc(), Mix.id.desc()).limit(5))).all()
    liked = [m.name[:100] for m in rated if m.rating == 1][:20]
    disliked = [m.name[:100] for m in rated if m.rating == -1][:20]
    await session.commit()  # Never hold a database transaction during the provider call.
    async with limiter.reserve(telegram_id):
        recommendation = await llm_service.generate_mix(tobaccos=collection, **data.model_dump(),
                                                        liked_mixes=liked, disliked_mixes=disliked,
                                                        previous_mixes=[n[:100] for n in recent])
        try:
            recommendation = MixRecommendation.model_validate(recommendation.model_dump()).validate_collection(names, data.base_tobacco)
        except (ValidationError, ValueError):
            raise GenerationUnavailable() from None
        item = Mix(user_id=user_id, name=recommendation.name,
                   components={c.tobacco: {'portion': c.portion, 'role': c.role} for c in recommendation.components},
                   description=recommendation.description, tips=recommendation.tips, request_type=data.request_type)
        session.add(item)
        await session.commit()
        return item, recommendation
