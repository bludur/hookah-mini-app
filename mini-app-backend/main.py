import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, delete, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hookah_core.auth import InvalidInitData, validate_init_data
from hookah_core.config import settings
from hookah_core.database import engine, init_db, get_session
from hookah_core.errors import DomainError
from hookah_core.limits import limiter
from hookah_core.llm import llm_service
from hookah_core.photos import PhotoRequest, PhotoResult, MAX_UPLOAD_BODY, photo_limiter, recognize_photo
from hookah_core.models import User, Category, Tobacco, Mix
from hookah_core import services
from schemas import (UserResponse, CategoryResponse, TobaccoCreate, TobaccoUpdate, TobaccoResponse,
                     TobaccoBulkCreate, TobaccoBulkResponse, MixResponse, MixGenerateRequest,
                     MixGenerateResponse, MixRateRequest, MixFavoriteRequest, StatsResponse)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    settings.validate_runtime()
    try:
        await init_db()
        await limiter.start()
        yield
    finally:
        await llm_service.close()
        await limiter.close()
        await photo_limiter.close()
        await engine.dispose()


app = FastAPI(title='Hookah Mix API', version='1.1.0', lifespan=lifespan,
              docs_url='/docs' if settings.app_env != 'production' else None,
              redoc_url=None, openapi_url='/openapi.json' if settings.app_env != 'production' else None)


class RequestBoundary:
    """Bound buffered JSON bodies, including requests without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def safe_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'x-content-type-options', b'nosniff'), (b'cache-control', b'no-store')]
            await send(message)

        is_photo = scope.get('path') == '/api/tobaccos/recognize-photo' and scope.get('method') == 'POST'
        if is_photo:
            try:
                header = dict(scope.get('headers', [])).get(b'x-telegram-init-data', b'').decode('ascii')
                validate_init_data(header, settings.bot_token.get_secret_value(), settings.telegram_auth_max_age)
            except (InvalidInitData, UnicodeError):
                return await JSONResponse({'detail': 'Откройте приложение в Telegram.'}, status_code=401)(scope, receive, safe_send)
        maximum = MAX_UPLOAD_BODY if is_photo else 65536
        body = bytearray()
        try:
            async with asyncio.timeout(15):
                while True:
                    event = await receive()
                    if event['type'] == 'http.disconnect':
                        return
                    chunk = event.get('body', b'')
                    if len(body) + len(chunk) > maximum:
                        return await JSONResponse({'detail': 'Запрос слишком большой'}, status_code=413)(scope, receive, safe_send)
                    body.extend(chunk)
                    if not event.get('more_body', False):
                        break
        except TimeoutError:
            return await JSONResponse({'detail': 'Загрузка заняла слишком много времени'}, status_code=408)(scope, receive, safe_send)
        delivered = False

        async def buffered_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, buffered_receive, safe_send)


app.add_middleware(RequestBoundary)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
                   allow_headers=['Content-Type', 'X-Telegram-Init-Data'], expose_headers=['Retry-After'])


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    headers = {'Retry-After': str(exc.retry_after)} if exc.retry_after else None
    return JSONResponse({'detail': str(exc)}, status_code=exc.status_code, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({'detail': 'Проверьте заполнение и длину полей запроса.'}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error('Request failed (%s)', type(exc).__name__)
    return JSONResponse({'detail': 'Внутренняя ошибка. Попробуйте позже.'}, status_code=500,
                        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


async def get_current_user(
    init_data: Annotated[str | None, Header(alias='X-Telegram-Init-Data')] = None,
    session: AsyncSession = Depends(get_session),
):
    try:
        identity = validate_init_data(init_data or '', settings.bot_token.get_secret_value(), settings.telegram_auth_max_age)
    except InvalidInitData:
        raise HTTPException(401, 'Сессия истекла или недействительна. Откройте приложение заново в Telegram.') from None
    return await services.get_or_create_user(session, identity.id, identity.username, identity.first_name)


Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0, le=1000000)]


@app.get('/api/user/me', response_model=UserResponse)
async def get_me(user: CurrentUser):
    return user


@app.get('/api/user/stats', response_model=StatsResponse)
async def get_stats(user: CurrentUser, session: Session):
    return StatsResponse(
        tobaccos_count=await session.scalar(select(func.count(Tobacco.id)).where(Tobacco.user_id == user.id)),
        mixes_count=await session.scalar(select(func.count(Mix.id)).where(Mix.user_id == user.id)),
        favorites_count=await session.scalar(select(func.count(Mix.id)).where(Mix.user_id == user.id, Mix.is_favorite.is_(True))),
    )


@app.get('/api/categories', response_model=list[CategoryResponse])
async def get_categories(session: Session):
    return (await session.scalars(select(Category).order_by(Category.name))).all()


@app.get('/api/tobaccos', response_model=list[TobaccoResponse])
async def get_tobaccos(user: CurrentUser, session: Session):
    return (await session.scalars(select(Tobacco).where(Tobacco.user_id == user.id)
                                 .options(selectinload(Tobacco.category)).order_by(Tobacco.name))).all()


@app.post('/api/tobaccos/recognize-photo', response_model=PhotoResult)
async def recognize_tobaccos(data: PhotoRequest, user: CurrentUser, session: Session):
    await session.commit()
    return await recognize_photo(data.image, user.telegram_id)


@app.get('/api/tobaccos/{tobacco_id}', response_model=TobaccoResponse)
async def get_tobacco(tobacco_id: int, user: CurrentUser, session: Session):
    return await services.load_tobacco(session, user.id, tobacco_id)


@app.post('/api/tobaccos', response_model=TobaccoResponse, status_code=201)
async def create_tobacco(data: TobaccoCreate, user: CurrentUser, session: Session):
    return await services.create_tobacco(session, user.id, data)


@app.post('/api/tobaccos/bulk', response_model=TobaccoBulkResponse)
async def create_tobaccos_bulk(data: TobaccoBulkCreate, user: CurrentUser, session: Session):
    return await services.bulk_tobaccos(session, user.id, data.tobaccos)


@app.put('/api/tobaccos/{tobacco_id}', response_model=TobaccoResponse)
async def update_tobacco(tobacco_id: int, data: TobaccoUpdate, user: CurrentUser, session: Session):
    return await services.update_tobacco(session, user.id, tobacco_id, data)


@app.delete('/api/tobaccos/{tobacco_id}')
async def delete_tobacco(tobacco_id: int, user: CurrentUser, session: Session):
    item = await services.load_tobacco(session, user.id, tobacco_id)
    await session.delete(item)
    await session.commit()
    return {'message': 'Табак удалён'}


@app.delete('/api/tobaccos')
async def delete_all_tobaccos(user: CurrentUser, session: Session):
    await session.execute(delete(Tobacco).where(Tobacco.user_id == user.id))
    await session.commit()
    return {'message': 'Коллекция очищена'}


@app.post('/api/mixes/generate', response_model=MixGenerateResponse)
async def generate_mix(data: MixGenerateRequest, user: CurrentUser, session: Session):
    item, recommendation = await services.generate_mix(session, user, data)
    return MixGenerateResponse(id=item.id, **recommendation.model_dump())


@app.get('/api/mixes', response_model=list[MixResponse])
async def get_mixes(user: CurrentUser, session: Session, limit: PageLimit = 20, offset: PageOffset = 0):
    return (await session.scalars(select(Mix).where(Mix.user_id == user.id)
                                 .order_by(Mix.created_at.desc(), Mix.id.desc()).limit(limit).offset(offset))).all()


@app.get('/api/mixes/favorites', response_model=list[MixResponse])
async def get_favorites(user: CurrentUser, session: Session, limit: PageLimit = 20, offset: PageOffset = 0):
    return (await session.scalars(select(Mix).where(Mix.user_id == user.id, Mix.is_favorite.is_(True))
                                 .order_by(Mix.created_at.desc(), Mix.id.desc()).limit(limit).offset(offset))).all()


async def owned_mix(session, user_id, mix_id):
    item = (await session.scalars(select(Mix).where(Mix.id == mix_id, Mix.user_id == user_id))).one_or_none()
    if item is None:
        raise HTTPException(404, 'Микс не найден')
    return item


@app.get('/api/mixes/{mix_id}', response_model=MixResponse)
async def get_mix(mix_id: int, user: CurrentUser, session: Session):
    return await owned_mix(session, user.id, mix_id)


@app.post('/api/mixes/{mix_id}/rate', response_model=MixResponse)
async def rate_mix(mix_id: int, data: MixRateRequest, user: CurrentUser, session: Session):
    item = await owned_mix(session, user.id, mix_id)
    item.rating = data.rating
    await session.commit()
    return item


@app.post('/api/mixes/{mix_id}/favorite', response_model=MixResponse)
async def toggle_favorite(mix_id: int, data: MixFavoriteRequest, user: CurrentUser, session: Session):
    item = await owned_mix(session, user.id, mix_id)
    item.is_favorite = data.is_favorite
    await session.commit()
    return item


@app.delete('/api/mixes/favorites')
async def clear_favorites(user: CurrentUser, session: Session):
    await session.execute(update(Mix).where(Mix.user_id == user.id).values(is_favorite=False))
    await session.commit()
    return {'message': 'Избранное очищено'}


@app.get('/healthz', include_in_schema=False)
async def liveness():
    # Platform probes must not keep a serverless database awake and consume its quota.
    # Startup still checks migrations and Redis; /api/health checks database readiness.
    return {'status': 'ok'}


@app.get('/api/health')
async def health_check(session: Session):
    await session.execute(text('SELECT 1'))
    return {'status': 'ok'}
