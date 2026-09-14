import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from sqlalchemy import func, select
from conftest import auth
from hookah_core import photos
from hookah_core.config import settings
from hookah_core.errors import DomainError
from hookah_core.limits import GenerationLimiter
from hookah_core.models import Tobacco

def photo(width=100, height=80):
    output = io.BytesIO()
    image = Image.new('RGB', (width, height), 'red')
    exif = Image.Exif(); exif[270] = 'private metadata'
    image.save(output, 'JPEG', exif=exif)
    return base64.b64encode(output.getvalue()).decode()

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(settings, 'llm_api_url', 'https://openrouter.ai/api/v1')
    monkeypatch.setattr(photos, 'photo_limiter', GenerationLimiter(settings, 'test-photos'))
    monkeypatch.setattr(photos, 'limiter', GenerationLimiter(settings))
    result = {'tobaccos': [{'name': 'Mango', 'brand': 'Example'}], 'unreadable': False}
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(result)))]))
    monkeypatch.setattr(photos.llm_service, '_client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return create

def test_photo_reencode_strips_metadata_and_bounds_dimensions():
    result = photos.sanitize_image(photo(1900, 1000))
    with Image.open(io.BytesIO(base64.b64decode(result))) as image:
        assert image.format == 'JPEG'
        assert image.width == 1600
        assert not image.getexif()

@pytest.mark.parametrize('encoded', ['https://example.com/private.jpg', base64.b64encode(b'<svg/>').decode(), photo(20, 20), photo(2100, 2000)], ids=['remote-url', 'svg', 'too-small', 'pixel-limit'])
def test_rejects_urls_fake_images_and_excessive_dimensions(encoded):
    with pytest.raises(DomainError): photos.sanitize_image(encoded)

async def test_photo_requires_auth_before_provider(api, provider):
    assert (await api.post('/api/tobaccos/recognize-photo', json={'image': photo()})).status_code == 401
    provider.assert_not_called()

async def test_photo_preview_never_writes_and_caps_price(api, provider, db):
    response = await api.post('/api/tobaccos/recognize-photo', headers=auth(), json={'image': photo()})
    assert response.status_code == 200
    assert response.json()['tobaccos'][0]['brand'] == 'Example'
    async with db() as session:
        assert await session.scalar(select(func.count(Tobacco.id))) == 0
    options = provider.call_args.kwargs
    assert options['model'] == 'inclusionai/ling-3.0-flash-vl:free'
    assert options['extra_body']['reasoning'] == {'enabled': False}
    assert options['extra_body']['provider']['max_price'] == {'prompt': 0, 'completion': 0}
    assert options['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')

async def test_photo_upload_bound_does_not_relax_other_endpoints(api, provider):
    assert (await api.post('/api/tobaccos/recognize-photo', headers=auth(), content=b'x'*(photos.MAX_UPLOAD_BODY+1))).status_code == 413
    assert (await api.post('/api/tobaccos/bulk', headers=auth(), content=b'x'*65537)).status_code == 413
    assert (await api.post('/api/tobaccos/recognize-photo', headers=auth(), json={'image': 'a'*100})).status_code == 422
    provider.assert_not_called()

async def test_photo_quota_and_malformed_provider_fail_closed(api, provider, monkeypatch):
    limited = settings.model_copy(update={'generation_daily_limit': 1})
    monkeypatch.setattr(photos, 'photo_limiter', GenerationLimiter(limited, 'test-photos'))
    provider.return_value.choices[0].message.content = '{"tobaccos": [{"name":"Mango","secret":"bad"}]}'
    response = await api.post('/api/tobaccos/recognize-photo', headers=auth(), json={'image': photo()})
    assert response.status_code == 503
    assert 'secret' not in response.text
    assert (await api.post('/api/tobaccos/recognize-photo', headers=auth(), json={'image': photo()})).status_code == 429
    assert provider.await_count == 1

async def test_brands_distinguish_products_and_normalize_conflicts(api):
    async def add(brand):
        return await api.post('/api/tobaccos', headers=auth(), json={'name': 'Mango', 'brand': brand})
    first = await add('Brand A'); second = await add('Brand B')
    assert first.status_code == second.status_code == 201
    assert (await add('  BRAND a  ')).status_code == 409
    assert (await api.put(f"/api/tobaccos/{second.json()['id']}", headers=auth(), json={'brand': 'Brand A'})).status_code == 409
    response = await api.post('/api/tobaccos/bulk', headers=auth(), json={'tobaccos': [{'name': 'Mango', 'brand': 'Brand A'}, {'name': 'Mango', 'brand': 'Brand C'}]})
    assert response.json()['added'] == ['Mango']
    assert response.json()['skipped'] == ['Mango']

async def test_base_id_disambiguates_flavors_without_cross_owner_access(api, monkeypatch):
    from hookah_core.llm import llm_service
    from hookah_core.schemas import MixRecommendation
    first = (await api.post('/api/tobaccos', headers=auth(), json={'name': 'Mango', 'brand': 'A'})).json()
    await api.post('/api/tobaccos', headers=auth(), json={'name': 'Mango', 'brand': 'B'})
    async def generate(**kwargs):
        names = [t['name'] for t in kwargs['tobaccos']]
        assert len(set(names)) == 2
        assert kwargs['base_tobacco'].startswith(f"#{first['id']}:")
        return MixRecommendation(name='Test mix', components=[{'tobacco': n, 'portion': 50, 'role': 'база' if n == kwargs['base_tobacco'] else 'акцент'} for n in names], description='Test', tips='Test')
    monkeypatch.setattr(llm_service, 'generate_mix', generate)
    assert (await api.post('/api/mixes/generate', headers=auth(), json={'request_type':'base','base_tobacco_id': first['id']})).status_code == 200
    assert (await api.post('/api/mixes/generate', headers=auth(), json={'request_type':'base','base_tobacco':'Mango'})).status_code == 422
    assert (await api.post('/api/mixes/generate', headers=auth(), json={'request_type':'base','base_tobacco_id': 999})).status_code == 422
