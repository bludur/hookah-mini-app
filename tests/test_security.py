import json
import time

import pytest
from aiogram.utils.web_app import check_webapp_signature
from hookah_core.auth import validate_init_data, InvalidInitData
from hookah_core.config import settings, Settings
from conftest import signed_data, auth


def test_valid_signature_matches_aiogram():
    raw = signed_data(2**51, signature='additional-signed-field')
    token = settings.bot_token.get_secret_value()
    assert check_webapp_signature(token, raw)
    user = validate_init_data(raw, token, 3600)
    assert user.id == 2**51 and user.first_name == 'Дмитрий'


@pytest.mark.parametrize('raw', ['', 'x=1', 'hash=' + '0' * 64, 'x' * 8200])
def test_malformed_auth(raw):
    with pytest.raises(InvalidInitData):
        validate_init_data(raw, settings.bot_token.get_secret_value(), 3600)


@pytest.mark.parametrize('offset', [-3601, 31])
def test_expired_and_future_auth(offset):
    now = int(time.time())
    with pytest.raises(InvalidInitData):
        validate_init_data(signed_data(issued=now + offset), settings.bot_token.get_secret_value(), 3600, now)


def test_tampering_duplicate_fields_and_wrong_bot():
    token = settings.bot_token.get_secret_value()
    for raw in [signed_data().replace('111111', '222222'), signed_data() + '&auth_date=1']:
        with pytest.raises(InvalidInitData):
            validate_init_data(raw, token, 3600)
    with pytest.raises(InvalidInitData):
        validate_init_data(signed_data(), 'different-token', 3600)


@pytest.mark.parametrize('user_id', [True, -1, '123', 2**53])
def test_invalid_signed_user_shape(user_id):
    with pytest.raises(InvalidInitData):
        validate_init_data(signed_data(user_id), settings.bot_token.get_secret_value(), 3600)


async def test_old_headers_cannot_impersonate(api):
    for headers in [{}, {'X-Telegram-User-Id': '111111'}, {'X-Telegram-Init-Data': signed_data().replace('111111', '222222')}]:
        assert (await api.get('/api/user/me', headers=headers)).status_code == 401
    response = await api.get('/api/user/me', headers={**auth(), 'X-Telegram-User-Id': '222222'})
    assert response.status_code == 200
    assert response.json()['telegram_id'] == 111111


async def test_body_limit_without_content_length(api):
    async def chunks():
        yield b'{' + b'x' * 40000
        yield b'x' * 30000
    response = await api.post('/api/tobaccos', headers=auth(), content=chunks())
    assert response.status_code == 413


async def test_cors_and_security_headers(api):
    response = await api.options('/api/tobaccos', headers={'Origin': 'https://untrusted.invalid', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'X-Telegram-Init-Data'})
    assert 'access-control-allow-origin' not in response.headers
    response = await api.get('/api/user/me', headers=auth())
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_production_rejects_unsafe_configuration():
    config = Settings(_env_file=None, app_env='production', bot_token='test', llm_api_key='test')
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        config.validate_runtime()
    config.database_url = 'postgresql+asyncpg://local/test'
    with pytest.raises(RuntimeError, match='REDIS_URL'):
        config.validate_runtime()
