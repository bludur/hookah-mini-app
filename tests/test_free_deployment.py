import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from hookah_core.config import Settings, settings
from hookah_core.errors import GenerationUnavailable
from hookah_core.llm import LLMService


async def test_neon_tls_uses_system_roots_with_hostname_verification(monkeypatch):
    import ssl
    import hookah_core.database as database
    original = database.create_async_engine
    captured = {}
    def capture(url, **options):
        captured.update(options)
        assert 'ssl' not in url.query
        return original(url, **options)
    monkeypatch.setattr(database, 'create_async_engine', capture)
    engine = database.make_engine('postgresql+asyncpg://test:test@example.invalid/db?ssl=verify-full')
    try:
        context = captured['connect_args']['ssl']
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        assert context.get_ca_certs()
    finally:
        await engine.dispose()


async def test_liveness_does_not_open_database(api):
    import main
    async def unavailable():
        raise RuntimeError('Database unavailable')
        yield
    main.app.dependency_overrides[main.get_session] = unavailable
    assert (await api.get('/healthz')).status_code == 200
    assert (await api.get('/api/health')).status_code == 500


@pytest.mark.parametrize('model,endpoint', [
    ('openai/gpt-4o-mini', 'https://openrouter.ai/api/v1'),
    ('openrouter/free', 'https://example.com/api/v1'),
    ('openrouter/free', 'http://openrouter.ai/api/v1'),
])
def test_free_mode_rejects_paid_or_untrusted_configuration(model, endpoint):
    config = Settings(_env_file=None, llm_free_only=True, llm_model=model, llm_api_url=endpoint)
    with pytest.raises(RuntimeError):
        config.validate_llm_budget()


async def test_free_mode_caps_provider_price_and_never_falls_back(valid_mix, monkeypatch):
    monkeypatch.setattr(settings, 'llm_free_only', True)
    monkeypatch.setattr(settings, 'llm_model', 'openrouter/free')
    monkeypatch.setattr(settings, 'llm_api_url', 'https://openrouter.ai/api/v1')
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(valid_mix)))])
    create = AsyncMock(return_value=completion)
    service = LLMService()
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'surprise')
    assert create.call_args.kwargs['extra_body']['provider']['max_price'] == {'prompt': 0, 'completion': 0}
    create.reset_mock()
    create.side_effect = RuntimeError('Free capacity exhausted')
    with pytest.raises(GenerationUnavailable):
        await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'surprise')
    assert create.await_count == 1
    create.reset_mock()
    monkeypatch.setattr(settings, 'llm_model', 'openai/gpt-4o-mini')
    with pytest.raises(GenerationUnavailable):
        await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'surprise')
    create.assert_not_called()
