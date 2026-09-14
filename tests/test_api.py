import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, func
from hookah_core import services
from hookah_core.models import Tobacco, User, Mix
from hookah_core.llm import llm_service
from hookah_core.schemas import MixRecommendation
from hookah_core.errors import GenerationUnavailable
from hookah_core.config import settings
from conftest import auth


async def add(api, name='Mango', **fields):
    return await api.post('/api/tobaccos', headers=auth(), json={'name': name, **fields})


async def test_ownership_all_tobacco_operations(api):
    created = await add(api)
    assert created.status_code == 201
    item_id = created.json()['id']
    for method, body in [('GET', None), ('PUT', {'name': 'Changed'}), ('DELETE', None)]:
        response = await api.request(method, f'/api/tobaccos/{item_id}', headers=auth(222222), json=body)
        assert response.status_code == 404
    await api.delete('/api/tobaccos', headers=auth(222222))
    assert (await api.get(f'/api/tobaccos/{item_id}', headers=auth())).status_code == 200


async def test_unicode_duplicate_and_rename_conflict(api):
    a = await add(api, '  Мята  ')
    b = await add(api, 'Манго')
    assert a.status_code == b.status_code == 201
    assert (await add(api, 'мЯтА')).status_code == 409
    assert (await api.put(f"/api/tobaccos/{b.json()['id']}", headers=auth(), json={'name': 'МЯТА'})).status_code == 409
    assert (await api.get('/api/tobaccos', headers=auth())).json()[0]['name'] in ['Мята', 'Манго']


async def test_concurrent_duplicate_creation(api):
    result = await asyncio.gather(add(api, 'Concurrent'), add(api, 'Concurrent'))
    assert sorted(r.status_code for r in result) == [201, 409]


async def test_clear_optional_fields_and_invalid_category(api):
    item = (await add(api, brand='Brand', category_id=1, notes='Note')).json()
    response = await api.put(f"/api/tobaccos/{item['id']}", headers=auth(), json={'brand': None, 'category_id': None, 'notes': None})
    assert response.status_code == 200
    assert all(response.json()[key] is None for key in ['brand', 'category_id', 'notes'])
    assert (await add(api, 'Other', category_id=999)).status_code == 422
    assert (await api.put(f"/api/tobaccos/{item['id']}", headers=auth(), json={'name': None})).status_code == 422


async def test_bulk_reports_bad_rows_without_discarding_valid(api):
    response = await api.post('/api/tobaccos/bulk', headers=auth(), json={'tobaccos': [{'name': 'Mango'}, {'name': 'mango'}, {'name': 'x'}, {'name': 'Bad category', 'category_id': 999}]})
    assert response.status_code == 200
    assert response.json()['added'] == ['Mango']
    assert response.json()['skipped'] == ['mango']
    assert len(response.json()['errors']) == 2


async def test_collection_capacity_serialized(api, monkeypatch):
    monkeypatch.setattr(settings, 'max_collection_size', 2)
    await add(api, 'First')
    result = await asyncio.gather(add(api, 'Second'), add(api, 'Third'))
    assert sorted(r.status_code for r in result) == [201, 409]


@pytest.mark.parametrize('payload', [{'request_type': 'base'}, {'request_type': 'profile'}, {'request_type': 'surprise', 'base_tobacco': 'Mint'}, {'request_type': 'profile', 'taste_profile': 'x' * 1000}])
async def test_generation_request_validation(api, payload):
    assert (await api.post('/api/mixes/generate', headers=auth(), json=payload)).status_code == 422


async def test_generate_rate_favorite_and_ownership(api, monkeypatch, valid_mix):
    await add(api)
    await add(api, 'Mint')
    generate = AsyncMock(return_value=MixRecommendation.model_validate(valid_mix))
    monkeypatch.setattr(llm_service, 'generate_mix', generate)
    response = await api.post('/api/mixes/generate', headers=auth(), json={'request_type': 'base', 'base_tobacco': 'Mango'})
    assert response.status_code == 200
    mix_id = response.json()['id']
    for endpoint, payload in [(f'/api/mixes/{mix_id}/rate', {'rating': 1}), (f'/api/mixes/{mix_id}/favorite', {'is_favorite': True})]:
        assert (await api.post(endpoint, headers=auth(222222), json=payload)).status_code == 404
        assert (await api.post(endpoint, headers=auth(), json=payload)).status_code == 200
    assert (await api.get(f'/api/mixes/{mix_id}', headers=auth(222222))).status_code == 404
    favorites = (await api.get('/api/mixes/favorites', headers=auth())).json()
    assert len(favorites) == 1 and favorites[0]['rating'] == 1
    assert favorites[0]['created_at'].endswith('+00:00')
    assert (await api.get('/api/mixes?limit=-1', headers=auth())).status_code == 422
    assert (await api.get('/api/mixes?limit=1&offset=1', headers=auth())).json() == []


async def test_provider_failure_never_persists_or_leaks(api, db, monkeypatch):
    await add(api)
    await add(api, 'Mint')
    monkeypatch.setattr(llm_service, 'generate_mix', AsyncMock(side_effect=GenerationUnavailable()))
    response = await api.post('/api/mixes/generate', headers=auth(), json={'request_type': 'surprise'})
    assert response.status_code == 503
    async with db() as session:
        assert await session.scalar(select(func.count(Mix.id))) == 0


async def test_server_errors_are_generic(api, monkeypatch):
    monkeypatch.setattr(services, 'create_tobacco', AsyncMock(side_effect=RuntimeError('private provider credential')))
    response = await add(api)
    assert response.status_code == 500
    assert 'credential' not in response.text


async def test_generation_rate_limit_returns_retry_after(api, monkeypatch, valid_mix):
    monkeypatch.setattr(settings, 'generation_hourly_limit', 1)
    await add(api)
    await add(api, 'Mint')
    monkeypatch.setattr(llm_service, 'generate_mix', AsyncMock(return_value=MixRecommendation.model_validate(valid_mix)))
    assert (await api.post('/api/mixes/generate', headers=auth(), json={'request_type': 'surprise'})).status_code == 200
    response = await api.post('/api/mixes/generate', headers=auth(), json={'request_type': 'surprise'})
    assert response.status_code == 429 and int(response.headers['retry-after']) > 0
