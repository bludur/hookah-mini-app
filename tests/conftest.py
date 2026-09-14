import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

os.environ.update(APP_ENV='test', BOT_TOKEN='123456789:test-token', LLM_API_KEY='test-key',
                  LLM_API_URL='http://127.0.0.1:1/v1', REDIS_URL='', DATABASE_URL='sqlite+aiosqlite:///:memory:')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'mini-app-backend'), str(ROOT)]

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker
import main as api_module
from hookah_core.database import make_engine
from hookah_core.models import User, Tobacco, Category, Mix
from hookah_core.config import settings
from hookah_core import services
from hookah_core.limits import GenerationLimiter


def signed_data(user_id=111111, issued=None, **extra):
    values = {'auth_date': str(int(time.time()) if issued is None else issued),
              'user': json.dumps({'id': user_id, 'first_name': 'Дмитрий', 'username': 'test'}, ensure_ascii=False), **extra}
    secret = hmac.new(b'WebAppData', settings.bot_token.get_secret_value().encode(), hashlib.sha256).digest()
    check = '\n'.join(f'{k}={v}' for k, v in sorted(values.items()))
    values['hash'] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def auth(user_id=111111):
    return {'X-Telegram-Init-Data': signed_data(user_id)}


@pytest.fixture
async def db(tmp_path):
    engine = make_engine('sqlite+aiosqlite:///' + (tmp_path / 'test.db').as_posix())
    def migrate(conn):
        config = Config(str(ROOT / 'alembic.ini'))
        config.attributes['connection'] = conn
        command.upgrade(config, 'head')
    async with engine.begin() as conn:
        await conn.run_sync(migrate)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add_all([User(id=1, telegram_id=111111), User(id=2, telegram_id=222222),
                         Category(id=1, name='Fruit', emoji='F', taste_profile='sweet')])
        await session.commit()
    yield factory
    await engine.dispose()


@pytest.fixture
async def api(db, monkeypatch):
    async def get_session():
        async with db() as session:
            yield session
    api_module.app.dependency_overrides[api_module.get_session] = get_session
    monkeypatch.setattr(services, 'limiter', GenerationLimiter(settings))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api_module.app, raise_app_exceptions=False), base_url='http://test') as client:
        yield client
    api_module.app.dependency_overrides.clear()


@pytest.fixture
def valid_mix():
    return {'name': 'Fresh Mix', 'components': [
        {'tobacco': 'Mango', 'portion': 60, 'role': 'база'},
        {'tobacco': 'Mint', 'portion': 40, 'role': 'акцент'}],
        'description': 'Fresh flavor', 'tips': 'Mix evenly'}
