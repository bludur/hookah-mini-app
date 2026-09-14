from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text
from hookah_core.database import make_engine
from conftest import ROOT


def migrate(connection, revision):
    config = Config(str(ROOT / 'alembic.ini'))
    config.attributes['connection'] = connection
    command.upgrade(config, revision)


@pytest.mark.parametrize('duplicate', [False, True])
async def test_legacy_migration_preserves_data_and_stops_on_duplicates(tmp_path, duplicate):
    engine = make_engine('sqlite+aiosqlite:///' + (tmp_path / 'legacy.db').as_posix())
    try:
        async with engine.begin() as conn:
            await conn.run_sync(migrate, '0001')
            await conn.execute(text("INSERT INTO users (id, telegram_id, created_at) VALUES (1, 11, '2026-01-01')"))
            await conn.execute(text("INSERT INTO tobaccos (id, user_id, name, created_at) VALUES (1, 1, 'Мята', '2026-01-01')"))
            if duplicate:
                await conn.execute(text("INSERT INTO tobaccos (id, user_id, name, created_at) VALUES (2, 1, 'мята', '2026-01-01')"))
            # This represents a pre-Alembic installation with the original schema.
            await conn.execute(text('DELETE FROM alembic_version'))
        if duplicate:
            with pytest.raises(RuntimeError, match='Duplicate tobacco ids'):
                async with engine.begin() as conn:
                    await conn.run_sync(migrate, 'head')
            async with engine.connect() as conn:
                assert await conn.scalar(text('SELECT COUNT(*) FROM tobaccos')) == 2
                columns = await conn.run_sync(lambda c: [v['name'] for v in inspect(c).get_columns('tobaccos')])
                assert 'normalized_name' not in columns
        else:
            async with engine.begin() as conn:
                await conn.run_sync(migrate, 'head')
                assert (await conn.execute(text('SELECT id, name, normalized_name FROM tobaccos'))).one() == (1, 'Мята', 'мята')
                await conn.run_sync(migrate, 'head')
                assert await conn.scalar(text('SELECT COUNT(*) FROM tobaccos')) == 1
    finally:
        await engine.dispose()


async def test_sqlite_foreign_keys_enabled(db):
    from sqlalchemy.exc import IntegrityError
    async with db() as session:
        assert await session.scalar(text('PRAGMA foreign_keys')) == 1
        with pytest.raises(IntegrityError):
            await session.execute(text("INSERT INTO tobaccos (user_id, name, normalized_name, created_at) VALUES (9999, 'Invalid', 'invalid', '2026-01-01')"))
