import asyncio
import hashlib
import os
import uuid
from unittest.mock import AsyncMock

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError
import main
from conftest import auth
from hookah_core.models import Mix, Tobacco
from hookah_core.sharing import ShareStore
from hookah_core.errors import DomainError

async def test_sharing_auth_ownership_and_minimal_snapshot(api, db, monkeypatch):
    store = AsyncMock()
    store.create.return_value = {'id': 'a'*64, 'token': 'x'*43, 'expires_at': 9999999999}
    monkeypatch.setattr(main, 'share_store', store)
    async with db() as session:
        session.add_all([Tobacco(user_id=1, name='Mango', brand='Brand', notes='private note'),
                         Tobacco(user_id=2, name='Secret tobacco'),
                         Mix(id=1, user_id=1, name='Fresh mix', components={'#7: Mango (Brand)': {'portion': 100, 'role': 'база'}}, description='Description', tips='Tip', request_type='base', rating=-1)])
        await session.commit()
    assert (await api.post('/api/shares', json={'kind': 'collection'})).status_code == 401
    assert (await api.post('/api/shares', headers=auth(222222), json={'kind':'mix','mix_id':1})).status_code == 404
    store.create.assert_not_called()
    assert (await api.post('/api/shares', headers=auth(), json={'kind':'collection'})).status_code == 201
    owner, snapshot = store.create.call_args.args
    assert owner == 1 and snapshot == {'kind':'collection','title':'Список табаков','tobaccos':[{'name':'Mango','brand':'Brand'}]}
    assert (await api.post('/api/shares', headers=auth(), json={'kind':'mix','mix_id':1})).status_code == 201
    snapshot = store.create.call_args.args[1]
    assert snapshot == {'kind':'mix','title':'Fresh mix','description':'Description','tips':'Tip','components':[{'name':'Mango (Brand)','portion':100,'role':'база'}]}
    for payload in [{'kind':'mix'}, {'kind':'collection','mix_id':1}, {'kind':'collection','owner':2}]:
        assert (await api.post('/api/shares', headers=auth(), json=payload)).status_code == 422

async def test_public_link_reads_without_telegram_and_rejects_bad_tokens(api, monkeypatch):
    store = AsyncMock(); store.open.return_value = {'kind':'collection','title':'List','tobaccos':[]}
    monkeypatch.setattr(main, 'share_store', store)
    result = await api.post('/api/shares/open', json={'token':'x'*43})
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert (await api.post('/api/shares/open', json={'token':'invalid'})).status_code == 422
    assert (await api.get('/api/shares')).status_code == 401
    assert (await api.delete('/api/shares/'+'a'*64)).status_code == 401
    assert (await api.delete('/api/shares/'+'a'*64, headers=auth(222222))).status_code == 200
    store.revoke.assert_awaited_once_with(2,'a'*64)

async def test_share_store_fails_closed_without_redis_or_on_outage():
    with pytest.raises(DomainError) as exc:
        await ShareStore(None).create(1, {})
    assert exc.value.status_code == 503
    redis = AsyncMock(); redis.eval.side_effect = ConnectionError('secret connection string')
    with pytest.raises(DomainError) as exc:
        await ShareStore(redis).open('x'*43, 'client')
    assert exc.value.status_code == 503 and 'secret' not in str(exc.value)

@pytest.mark.skipif(not os.getenv('TEST_REDIS_URL'), reason='No disposable Redis configured')
async def test_real_share_snapshot_revocation_expiry_and_atomic_caps():
    redis = Redis.from_url(os.environ['TEST_REDIS_URL'])
    prefix = 'share-test:{' + uuid.uuid4().hex + '}'
    store = ShareStore(redis, prefix)
    snapshot = {'kind':'collection','title':'List','tobaccos':[{'name':'Mango','brand':'A'}]}
    try:
        created = await store.create(1, snapshot)
        assert created['id'] == hashlib.sha256(created['token'].encode()).hexdigest()
        assert 0 < await redis.ttl(store.key(created['id'])) <= 7*86400
        snapshot['tobaccos'][0]['name'] = 'Changed later'
        public = await store.open(created['token'], 'friend')
        assert public['tobaccos'][0]['name'] == 'Mango' and 'owner' not in public
        assert 'token' not in (await store.list(1))[0]
        assert await store.list(2) == []
        with pytest.raises(DomainError): await store.revoke(2, created['id'])
        await store.revoke(1, created['id'])
        with pytest.raises(DomainError) as exc: await store.open(created['token'], 'friend')
        assert exc.value.status_code == 404
        expired = await store.create(1, snapshot)
        await redis.pexpire(store.key(expired['id']), 1)
        await asyncio.sleep(.02)
        with pytest.raises(DomainError): await store.open(expired['token'], 'friend')
        # Multiple API instances cannot race past the owner cap.
        results = await asyncio.gather(*(store.create(2, snapshot) for _ in range(12)), return_exceptions=True)
        assert sum(isinstance(result, dict) for result in results) == 10
        assert sum(isinstance(result, DomainError) for result in results) == 2
        token = next(result['token'] for result in results if isinstance(result, dict))
        for _ in range(60): await store.open(token, 'rate-test')
        with pytest.raises(DomainError) as exc: await store.open(token, 'rate-test')
        assert exc.value.status_code == 429
    finally:
        async for key in redis.scan_iter(match=prefix+':*'): await redis.delete(key)
        await redis.aclose()
