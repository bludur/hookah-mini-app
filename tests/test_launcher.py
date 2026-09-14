from unittest.mock import AsyncMock
import pytest
from aiogram.types import Message
from bot.launcher import launch_reply, webhook_secret
from bot.security import PrivateChatMiddleware
import main as api_module


def message(text='/app@dimon_hookah_mix_bot', kind='supergroup'):
    return Message.model_validate({'message_id': 10, 'date': 1, 'chat': {'id': -123, 'type': kind},
        'from': {'id': 55, 'is_bot': False, 'first_name': 'User'}, 'text': text,
        'message_thread_id': 42, 'entities': [{'type': 'bot_command', 'offset': 0, 'length': len(text)}]})


@pytest.mark.parametrize('text', ['/app', '/app@dimon_hookah_mix_bot', '/app@DIMON_HOOKAH_MIX_BOT'])
def test_public_launcher(text):
    reply = launch_reply(message(text), 'dimon_hookah_mix_bot')
    assert reply['message_thread_id'] == 42
    button = reply['reply_markup']['inline_keyboard'][0][0]
    assert button['url'] == 'https://t.me/dimon_hookah_mix_bot?startapp'
    assert 'web_app' not in button


@pytest.mark.parametrize('text', ['/app@someone_else_bot', '/collection', '/app extra', 'hello /app', '/application'])
def test_other_commands_are_not_launched(text):
    assert launch_reply(message(text), 'dimon_hookah_mix_bot') is None


async def test_group_launcher_does_not_enter_private_handlers():
    bot = AsyncMock()
    bot.me.return_value.username = 'dimon_hookah_mix_bot'
    handler = AsyncMock()
    await PrivateChatMiddleware()(handler, message(), {'bot': bot})
    bot.send_message.assert_awaited_once()
    handler.assert_not_awaited()
    await PrivateChatMiddleware()(handler, message('/collection'), {'bot': bot})
    handler.assert_not_awaited()


async def test_webhook_auth_and_public_reply(api, monkeypatch):
    sender = AsyncMock()
    monkeypatch.setattr(api_module, 'send_launch_reply', sender)
    cache = AsyncMock(return_value=True)
    monkeypatch.setattr(api_module.share_store, 'call', cache)
    payload = {'update_id': 42, 'message': message().model_dump(mode='json', by_alias=True)}
    assert (await api.post('/telegram/launcher', json=payload)).status_code == 403
    cache.assert_not_awaited()
    headers = {'X-Telegram-Bot-Api-Secret-Token': webhook_secret()}
    response = await api.post('/telegram/launcher', json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {'ok': True}
    assert sender.call_args.args[0]['chat_id'] == -123
    cache.return_value = False
    assert (await api.post('/telegram/launcher', json=payload, headers=headers)).json() == {'ok': True}
    payload['message'] = message('/collection').model_dump(mode='json', by_alias=True)
    cache.reset_mock()
    assert (await api.post('/telegram/launcher', json=payload, headers=headers)).json() == {'ok': True}
    cache.assert_not_awaited()


def test_anonymous_group_admin_can_open_app():
    event = message().model_copy(update={'sender_chat': message().chat, 'from_user': message().from_user.model_copy(update={'is_bot': True})})
    assert launch_reply(event, 'dimon_hookah_mix_bot') is not None


async def test_delivery_failure_allows_retry(api, monkeypatch):
    from hookah_core.errors import DomainError
    cache = AsyncMock(return_value=True)
    monkeypatch.setattr(api_module.share_store, 'call', cache)
    monkeypatch.setattr(api_module, 'send_launch_reply', AsyncMock(side_effect=DomainError('Failed', 503)))
    result = await api.post('/telegram/launcher', json={'update_id': 51, 'message': message().model_dump(mode='json', by_alias=True)},
                            headers={'X-Telegram-Bot-Api-Secret-Token': webhook_secret()})
    assert result.status_code == 503
    assert cache.call_args.args[0] == 'delete'
