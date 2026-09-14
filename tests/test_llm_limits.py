import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest
from redis.exceptions import ConnectionError
from hookah_core.config import settings
from hookah_core.errors import DomainError, GenerationUnavailable
from hookah_core.limits import GenerationLimiter
from hookah_core.llm import LLMService


@pytest.mark.parametrize('change', ['sum', 'unknown', 'duplicate', 'one', 'too_many', 'role', 'negative', 'float', 'empty', 'base', 'markdown', 'broken_json'])
async def test_rejects_invalid_provider_output(valid_mix, change):
    data = copy.deepcopy(valid_mix)
    if change == 'sum': data['components'][0]['portion'] = 130
    if change == 'unknown': data['components'][0]['tobacco'] = 'Missing'
    if change == 'duplicate': data['components'][1]['tobacco'] = 'Mango'
    if change == 'one': data['components'] = data['components'][:1]
    if change == 'too_many': data['components'] *= 3
    if change == 'role': data['components'][0]['role'] = 'instruction'
    if change == 'negative': data['components'][0]['portion'] = -10
    if change == 'float': data['components'][0]['portion'] = 60.0
    if change == 'empty': data['description'] = ''
    if change == 'base': data['components'][0]['role'], data['components'][1]['role'] = 'акцент', 'база'
    content = json.dumps(data)
    if change == 'markdown': content = 'Here is your mix! ' + content
    if change == 'broken_json': content = '{'
    service = LLMService()
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=completion))))
    with pytest.raises(GenerationUnavailable):
        await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'base', 'Mango')


async def test_provider_json_fence_and_valid_output(valid_mix):
    service = LLMService()
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='```json\n' + json.dumps(valid_mix) + '\n```'))])
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=completion))))
    result = await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'base', 'Mango')
    assert result.name == 'Fresh Mix'


async def test_provider_exception_does_not_expose_payload(caplog):
    service = LLMService()
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError('secret-text')))))
    with pytest.raises(GenerationUnavailable) as exc:
        await service.generate_mix([{'name': 'Mango'}, {'name': 'Mint'}], 'surprise')
    assert 'secret-text' not in str(exc.value) + caplog.text


@pytest.mark.parametrize('backend', ['memory', 'redis'])
async def test_concurrency_and_quota_across_instances(backend):
    config = settings.model_copy(update={'generation_hourly_limit': 2, 'generation_concurrency': 1})
    first = GenerationLimiter(config)
    second = first
    if backend == 'redis':
        server = fakeredis.FakeServer()
        first.redis = fakeredis.aioredis.FakeRedis(server=server)
        second = GenerationLimiter(config)
        second.redis = fakeredis.aioredis.FakeRedis(server=server)
    async with first.reserve(10):
        with pytest.raises(DomainError) as exc:
            async with second.reserve(10): pass
        assert exc.value.status_code == 429
        with pytest.raises(DomainError):
            async with second.reserve(20): pass
    # Failures release concurrency, but still count toward the spending budget.
    with pytest.raises(ValueError):
        async with second.reserve(10):
            raise ValueError('provider failed')
    with pytest.raises(DomainError):
        async with first.reserve(10): pass
    await first.close()
    if second is not first: await second.close()


async def test_redis_global_daily_budget():
    config = settings.model_copy(update={'generation_global_daily_limit': 1})
    limiter = GenerationLimiter(config)
    limiter.redis = fakeredis.aioredis.FakeRedis()
    async with limiter.reserve(10): pass
    with pytest.raises(DomainError):
        async with limiter.reserve(20): pass
    await limiter.close()


async def test_redis_failure_fails_closed():
    limiter = GenerationLimiter(settings)
    limiter.redis = SimpleNamespace(eval=AsyncMock(side_effect=ConnectionError('private connection data')))
    with pytest.raises(GenerationUnavailable):
        async with limiter.reserve(1): pass


async def test_production_never_uses_memory_fallback():
    limiter = GenerationLimiter(settings.model_copy(update={'app_env': 'production'}))
    with pytest.raises(GenerationUnavailable):
        async with limiter.reserve(1): pass
