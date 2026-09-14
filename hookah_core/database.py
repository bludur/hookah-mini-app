from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
import ssl

from .config import ROOT, settings
from .models import Category


def make_engine(url: str):
    options = {'connect_args': {'timeout': 15}} if url.startswith('sqlite') else {}
    parsed = make_url(url)
    if parsed.drivername == 'postgresql+asyncpg' and parsed.query.get('ssl') == 'verify-full':
        # asyncpg's string mode expects ~/.postgresql/root.crt. Use system roots
        # with certificate AND hostname verification on Windows and Render alike.
        options['connect_args'] = {'ssl': ssl.create_default_context()}
        parsed = parsed.difference_update_query(['ssl'])
    result = create_async_engine(parsed, pool_pre_ping=True, **options)
    if url.startswith('sqlite'):
        @event.listens_for(result.sync_engine, 'connect')
        def enable_foreign_keys(connection, record):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.close()
    return result


engine = make_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)

CATEGORIES = [
    ('Ягодные', '🍓', 'сладкий'), ('Цитрусовые', '🍊', 'кислый'),
    ('Фруктовые', '🍎', 'сладкий'), ('Тропические', '🥭', 'сладкий'),
    ('Мятные', '🍃', 'свежий'), ('Холодок', '❄️', 'свежий'),
    ('Десертные', '🍬', 'сладкий'), ('Напитки', '🥤', 'разный'),
    ('Цветочные', '🌸', 'нейтральный'), ('Пряные', '🌶', 'терпкий'),
]


def dialect_insert(session, model):
    if session.bind.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        from sqlalchemy.dialects.postgresql import insert
    return insert(model)


async def init_db():
    """Startup checks migrations; schema changes are a separate deployment step."""
    config = Config(str(ROOT / 'alembic.ini'))
    head = ScriptDirectory.from_config(config).get_current_head()
    async with engine.connect() as conn:
        revision = await conn.run_sync(lambda sync: MigrationContext.configure(sync).get_current_revision())
    if revision != head:
        raise RuntimeError('Database migrations required: run python -m alembic upgrade head')
    async with async_session() as session:
        for name, emoji, profile in CATEGORIES:
            stmt = dialect_insert(session, Category).values(name=name, emoji=emoji, taste_profile=profile)
            await session.execute(stmt.on_conflict_do_nothing(index_elements=['name']))
        await session.commit()


async def get_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
