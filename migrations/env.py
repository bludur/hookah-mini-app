import asyncio

from alembic import context
from hookah_core.config import settings
from hookah_core.database import make_engine
from hookah_core.models import Base


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True,
                      render_as_batch=connection.dialect.name == 'sqlite')
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = make_engine(settings.database_url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError('These migrations inspect existing data; use an online database connection')
elif context.config.attributes.get('connection') is not None:
    run_migrations(context.config.attributes['connection'])
else:
    asyncio.run(online())
