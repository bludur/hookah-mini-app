"""Revocable seven-day snapshots, bounded in the existing shared Redis store."""
import hashlib
import json
import secrets
import time
from typing import Literal

from pydantic import Field, model_validator
from redis.exceptions import RedisError

from .config import settings
from .errors import DomainError
from .limits import limiter
from .schemas import InputModel

TTL = 7 * 86400
CREATE = '''
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= 500 or redis.call('ZCARD', KEYS[2]) >= 10 then return 1 end
if tonumber(redis.call('GET', KEYS[3]) or '0') >= 20 then return 1 end
if not redis.call('SET', KEYS[4], ARGV[4], 'EX', ARGV[2], 'NX') then return 2 end
redis.call('ZADD', KEYS[1], tonumber(ARGV[1])+tonumber(ARGV[2]), ARGV[3])
redis.call('ZADD', KEYS[2], tonumber(ARGV[1])+tonumber(ARGV[2]), ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[2])
redis.call('EXPIRE', KEYS[2], ARGV[2])
redis.call('INCR', KEYS[3]); redis.call('EXPIRE', KEYS[3], 172800)
return 0
'''
OPEN = '''
if tonumber(redis.call('GET', KEYS[1]) or '0') >= 300 then return {429, ''} end
redis.call('INCR', KEYS[1]); redis.call('EXPIRE', KEYS[1], 120)
local count=redis.call('INCR', KEYS[2]); redis.call('EXPIRE', KEYS[2], 120)
if count > 60 then return {429, ''} end
return {200, redis.call('GET', KEYS[3]) or ''}
'''
REVOKE = '''
local raw=redis.call('GET', KEYS[1])
if not raw or tostring(cjson.decode(raw).owner) ~= ARGV[1] then return 0 end
redis.call('DEL', KEYS[1]); redis.call('ZREM', KEYS[2], ARGV[2]); redis.call('ZREM', KEYS[3], ARGV[2])
return 1
'''

class ShareCreate(InputModel):
    kind: Literal['mix', 'collection']
    mix_id: int | None = Field(None, gt=0)

    @model_validator(mode='after')
    def match_kind(self):
        if (self.kind == 'mix') != (self.mix_id is not None):
            raise ValueError('Choose a mix or a collection')
        return self

class ShareOpen(InputModel):
    token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]{43}$')

class ShareStore:
    def __init__(self, redis, prefix=None):
        self.redis = redis
        self.prefix = prefix or f'hookah:{{{settings.app_env}:{settings.bot_token.get_secret_value().split(":", 1)[0]}}}:shares'

    async def call(self, method, *args, **kwargs):
        if self.redis is None:
            raise DomainError('Ссылки временно недоступны. Попробуйте позже.', 503)
        try:
            return await getattr(self.redis, method)(*args, **kwargs)
        except RedisError:
            raise DomainError('Ссылки временно недоступны. Попробуйте позже.', 503) from None

    def key(self, suffix):
        return f'{self.prefix}:{suffix}'

    async def create(self, owner, snapshot):
        token = secrets.token_urlsafe(32)
        identifier = hashlib.sha256(token.encode()).hexdigest()
        now = int(time.time())
        public = {**snapshot, 'created_at': now, 'expires_at': now + TTL}
        raw = json.dumps({'owner': owner, 'public': public}, ensure_ascii=False)
        if len(raw.encode()) > 131072:
            raise DomainError('Список слишком большой для одной ссылки.', 422)
        result = await self.call('eval', CREATE, 4, self.key('all'), self.key(f'owner:{owner}'),
                                 self.key(f'day:{now // 86400}:{owner}'), self.key(identifier), now, TTL, identifier, raw)
        if result == 1:
            raise DomainError('Пока нельзя создать ещё одну ссылку. Отключите ненужные или попробуйте позже.', 429, 3600)
        if result != 0:
            raise DomainError('Не удалось создать ссылку. Попробуйте ещё раз.', 503)
        return {'id': identifier, 'token': token, 'expires_at': now + TTL}

    async def open(self, token, client):
        identifier = hashlib.sha256(token.encode()).hexdigest()
        minute = int(time.time()) // 60
        # Hash the address; no IPs or bearer tokens are stored in readable keys/logs.
        address = hashlib.sha256(client.encode()).hexdigest()
        code, raw = await self.call('eval', OPEN, 3, self.key(f'read:{minute}'),
                                    self.key(f'read:{minute}:{address}'), self.key(identifier))
        if code == 429:
            raise DomainError('Слишком много открытий. Попробуйте через минуту.', 429, 60)
        if not raw:
            raise DomainError('Ссылка недоступна: срок истёк или владелец её отключил.', 404)
        public = json.loads(raw)['public']
        if public['expires_at'] <= time.time():
            raise DomainError('Ссылка недоступна: срок истёк или владелец её отключил.', 404)
        return public

    async def list(self, owner):
        identifiers = await self.call('zrangebyscore', self.key(f'owner:{owner}'), int(time.time()) + 1, '+inf')
        if not identifiers:
            return []
        identifiers = [value.decode() if isinstance(value, bytes) else value for value in identifiers]
        values = await self.call('mget', [self.key(value) for value in identifiers])
        result = []
        for identifier, raw in zip(identifiers, values):
            if not raw:
                continue
            record = json.loads(raw)
            if record['owner'] != owner:
                continue
            public = record['public']
            result.append({'id': identifier, 'kind': public['kind'], 'title': public['title'],
                           'created_at': public['created_at'], 'expires_at': public['expires_at']})
        return result

    async def revoke(self, owner, identifier):
        result = await self.call('eval', REVOKE, 3, self.key(identifier), self.key('all'),
                                 self.key(f'owner:{owner}'), str(owner), identifier)
        if not result:
            raise DomainError('Ссылка не найдена.', 404)

share_store = ShareStore(limiter.redis)
