import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .config import settings
from .errors import DomainError, GenerationUnavailable

logger = logging.getLogger(__name__)

# All checks and reservations are atomic across the API and bot processes.
ACQUIRE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('EXISTS', KEYS[2]) == 1 then return 1 end
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[4]) then return 1 end
for i = 3, 5 do
  if tonumber(redis.call('GET', KEYS[i]) or '0') >= tonumber(ARGV[i+2]) then return 2 end
end
redis.call('SET', KEYS[2], ARGV[3], 'EX', ARGV[2])
redis.call('ZADD', KEYS[1], tonumber(ARGV[1])+tonumber(ARGV[2]), ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[2])
for i = 3, 5 do
  redis.call('INCR', KEYS[i])
  redis.call('EXPIRE', KEYS[i], 172800)
end
return 0
"""
RELEASE = """
redis.call('ZREM', KEYS[1], ARGV[1])
if redis.call('GET', KEYS[2]) == ARGV[1] then redis.call('DEL', KEYS[2]) end
return 0
"""


class GenerationLimiter:
    def __init__(self, config=settings):
        self.config = config
        self.redis = Redis.from_url(config.redis_url.get_secret_value(), socket_timeout=3, socket_connect_timeout=3) if config.redis_url.get_secret_value() else None
        self._lock = asyncio.Lock()
        self._active: dict[int, float] = {}
        self._counts: dict[tuple, tuple[int, float]] = {}

    async def start(self):
        if self.redis:
            await self.redis.ping()
        elif self.config.app_env == 'production':
            raise RuntimeError('Shared generation limits require Redis')

    async def close(self):
        if self.redis:
            await self.redis.aclose()

    @asynccontextmanager
    async def reserve(self, telegram_id: int):
        now = int(time.time())
        token = uuid.uuid4().hex
        lease = self.config.llm_timeout_seconds + 20
        bot_id = self.config.bot_token.get_secret_value().split(':', 1)[0]
        # A hash tag keeps keys in one slot when using Redis Cluster.
        prefix = f'hookah:{{{self.config.app_env}:{bot_id}}}'
        keys = [f'{prefix}:active', f'{prefix}:user:{telegram_id}:active',
                f'{prefix}:hour:{now // 3600}:{telegram_id}',
                f'{prefix}:day:{now // 86400}:{telegram_id}', f'{prefix}:day:{now // 86400}:all']
        caps = [self.config.generation_hourly_limit, self.config.generation_daily_limit, self.config.generation_global_daily_limit]
        if self.redis:
            try:
                code = await self.redis.eval(ACQUIRE, len(keys), *keys, now, lease, token, self.config.generation_concurrency, *caps)
            except RedisError:
                logger.warning('Generation limiter unavailable')
                raise GenerationUnavailable() from None
        else:
            if self.config.app_env == 'production':
                raise GenerationUnavailable()
            async with self._lock:
                self._active = {u: expiry for u, expiry in self._active.items() if expiry > now}
                self._counts = {k: value for k, value in self._counts.items() if value[1] > now}
                buckets = [('hour', telegram_id, now // 3600), ('day', telegram_id, now // 86400), ('all', now // 86400)]
                code = 0
                if telegram_id in self._active or len(self._active) >= self.config.generation_concurrency:
                    code = 1
                elif any(self._counts.get(k, (0, 0))[0] >= cap for k, cap in zip(buckets, caps)):
                    code = 2
                else:
                    self._active[telegram_id] = now + lease
                    for k in buckets:
                        self._counts[k] = (self._counts.get(k, (0, 0))[0] + 1, now + 172800)
        if code:
            text = 'Генерация уже выполняется. Подождите.' if code == 1 else 'Лимит генераций исчерпан. Попробуйте позже.'
            raise DomainError(text, 429, lease if code == 1 else 3600)
        try:
            yield
        finally:
            if self.redis:
                try:
                    await self.redis.eval(RELEASE, 2, *keys[:2], token)
                except RedisError:
                    # Lease expiration releases slots even after process/Redis failures.
                    logger.warning('Generation lease release deferred to expiration')
            else:
                async with self._lock:
                    self._active.pop(telegram_id, None)


limiter = GenerationLimiter()
