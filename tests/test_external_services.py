"""CI integration checks; only explicit, disposable test services are used."""
import os
import uuid

import pytest
from redis.asyncio import Redis
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from hookah_core.config import settings
from hookah_core.limits import GenerationLimiter
from hookah_core.errors import DomainError
from test_migrations import migrate


@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'), reason='No disposable PostgreSQL configured')
async def test_postgres_migrations_and_integrity():
    # Random schema in the explicitly supplied test DB; never touch public tables.
    schema = 'hookah_test_' + uuid.uuid4().hex
    url = os.environ['TEST_POSTGRES_URL']
    admin = create_async_engine(url)
    engine = create_async_engine(url, connect_args={'server_settings': {'search_path': schema}})
    try:
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA {schema}'))
        async with engine.begin() as conn:
            await conn.run_sync(migrate, 'head')
            tables = await conn.run_sync(lambda c: inspect(c).get_table_names(schema=schema))
            assert {'users', 'tobaccos', 'mixes', 'categories'} <= set(tables)
            constraints = await conn.run_sync(lambda c: inspect(c).get_unique_constraints('tobaccos', schema=schema))
            assert any(c['name'] == 'uq_tobacco_owner_name' for c in constraints)
            await conn.run_sync(migrate, 'head')
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        await admin.dispose()


@pytest.mark.skipif(not os.getenv('TEST_REDIS_URL'), reason='No disposable Redis configured')
async def test_real_redis_atomic_reservations():
    # Unique namespace; no FLUSHDB and no other application's counters are touched.
    namespace = uuid.uuid4().hex
    config = settings.model_copy(update={'bot_token': __import__('pydantic').SecretStr(namespace + ':test'), 'generation_hourly_limit': 1})
    one, two = GenerationLimiter(config), GenerationLimiter(config)
    one.redis, two.redis = Redis.from_url(os.environ['TEST_REDIS_URL']), Redis.from_url(os.environ['TEST_REDIS_URL'])
    try:
        await one.start()
        async with one.reserve(1):
            with pytest.raises(DomainError):
                async with two.reserve(1): pass
        with pytest.raises(DomainError):
            async with two.reserve(1): pass
    finally:
        prefix = f'hookah:{{{config.app_env}:{namespace}}}:*'
        async for key in one.redis.scan_iter(match=prefix):
            await one.redis.delete(key)
        await one.close()
        await two.close()
