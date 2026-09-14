from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message, Chat, User as TelegramUser
from sqlalchemy import select
from bot.handlers import collection, mix
from bot.security import escape_md, PrivateChatMiddleware, CommandView
from hookah_core.errors import DomainError
from hookah_core.models import Tobacco, Mix


def callback(data, user_id=222222):
    return SimpleNamespace(data=data, from_user=SimpleNamespace(id=user_id, username=None, first_name=None),
                           answer=AsyncMock(), message=SimpleNamespace(edit_text=AsyncMock(), edit_reply_markup=AsyncMock()))


@pytest.fixture
async def owned(db):
    async with db() as session:
        tobacco = Tobacco(user_id=1, name='Mango')
        recipe = Mix(user_id=1, name='Recipe', components={}, request_type='surprise')
        session.add_all([tobacco, recipe])
        await session.commit()
        return tobacco.id, recipe.id


async def test_foreign_tobacco_callbacks(db, owned):
    tobacco_id, _ = owned
    for handler, prefix in [(collection.show_tobacco, 'tobacco'), (collection.confirm_delete, 'delete_tobacco'), (collection.delete_tobacco, 'confirm_delete')]:
        async with db() as session:
            event = callback(f'{prefix}:{tobacco_id}')
            await handler(event, session)
            assert await session.get(Tobacco, tobacco_id) is not None
            assert not any('Mango' in str(call) for call in event.message.edit_text.call_args_list)


async def test_foreign_mix_callbacks(db, owned):
    _, mix_id = owned
    async with db() as session:
        await mix.rate_mix(callback(f'rate_mix:{mix_id}:1'), session)
        await mix.favorite_mix(callback(f'favorite_mix:{mix_id}'), session)
        item = await session.get(Mix, mix_id)
        assert item.rating is None and item.is_favorite is False
        await mix.rate_mix(callback(f'rate_mix:{mix_id}:99', 111111), session)
        assert item.rating is None


async def test_forged_bulk_selection_cannot_delete_foreign_tobacco(db, owned):
    state = AsyncMock()
    state.get_data.return_value = {'selected': [owned[0]]}
    async with db() as session:
        await collection.delete_selected_tobaccos(callback('confirm_delete_selected'), state, session)
        assert await session.get(Tobacco, owned[0]) is not None
    async with db() as session:
        with pytest.raises(DomainError):
            await collection.toggle_delete_selection(callback(f'toggle_delete:{owned[0]}'), state, session)


async def test_foreign_base_cannot_reach_generation(db, owned, monkeypatch):
    generation = AsyncMock()
    monkeypatch.setattr(mix.services, 'generate_mix', generation)
    async with db() as session:
        await mix.generate_mix_by_tobacco(callback(f'mix_with:{owned[0]}'), session, AsyncMock())
    generation.assert_not_awaited()


async def test_private_chat_guard():
    handler = AsyncMock()
    message = Message(message_id=1, date=1, chat=Chat(id=-10, type='group'), from_user=TelegramUser(id=1, is_bot=False, first_name='Test'), text='/start')
    await PrivateChatMiddleware()(handler, message, {})
    handler.assert_not_awaited()


def test_markdown_escape():
    assert escape_md('user_[click](url)*`\\') == r'user\_\[click](url)\*\`\\'


async def test_owner_edit_and_commands(db, owned):
    message = SimpleNamespace(from_user=SimpleNamespace(id=111111, username=None, first_name=None), text='New Mango | ', answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {'tobacco_id': owned[0]}
    async with db() as session:
        await collection.save_tobacco_edit(message, state, session)
        item = await session.get(Tobacco, owned[0])
        assert item.name == 'New Mango' and item.brand is None
        await collection.cmd_collection(message, state, session)
        await collection.cmd_add(message, state)
        await mix.cmd_mix(message, state, session)
    assert message.answer.await_count >= 4


async def test_dispatcher_routes_commands_during_form_entry(db, monkeypatch):
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.types import Update
    from bot.handlers import start
    import bot.main as bot_main
    monkeypatch.setattr(bot_main, 'async_session', db)
    bot = Bot(token='123456789:test-token')
    bot.session = AsyncMock()
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(bot_main.DatabaseMiddleware())
    dp.message.outer_middleware(PrivateChatMiddleware())
    dp.include_routers(start.router, collection.router, mix.router)
    try:
        for number, command in enumerate(['/add', '/mix', '/collection', '/start'], 1):
            message = Message(message_id=number, date=1, chat=Chat(id=111111, type='private'),
                              from_user=TelegramUser(id=111111, is_bot=False, first_name='Test'), text=command)
            await dp.feed_update(bot, Update(update_id=number, message=message))
        assert bot.session.await_count == 4
        async with db() as session:
            assert not list(await session.scalars(select(Tobacco)))
    finally:
        await storage.close()
