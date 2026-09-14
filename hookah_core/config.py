from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_env: Literal['development', 'test', 'production'] = 'development'
    bot_token: SecretStr = SecretStr('')
    bot_username: str = Field('dimon_hookah_mix_bot', pattern=r'^[A-Za-z0-9_]{5,32}$')
    database_url: str = 'sqlite+aiosqlite:///' + (ROOT / 'hookah_app.db').as_posix()
    redis_url: SecretStr = SecretStr('')
    cors_origins: str = 'http://localhost:3000,http://127.0.0.1:3000'
    telegram_auth_max_age: int = Field(3600, ge=60, le=86400)
    llm_api_url: str = 'https://api.openai.com/v1'
    llm_api_key: SecretStr = SecretStr('')
    llm_model: str = 'gpt-4o-mini'
    llm_free_only: bool = False
    llm_max_tokens: int = Field(1000, ge=100, le=4000)
    llm_temperature: float = Field(0.8, ge=0, le=2)
    llm_timeout_seconds: int = Field(40, ge=5, le=120)
    generation_hourly_limit: int = Field(10, ge=1, le=100)
    generation_daily_limit: int = Field(30, ge=1, le=1000)
    generation_global_daily_limit: int = Field(1000, ge=1, le=100000)
    generation_concurrency: int = Field(4, ge=1, le=32)
    photo_daily_limit: int = Field(3, ge=1, le=50)
    photo_global_daily_limit: int = Field(20, ge=1, le=1000)
    max_collection_size: int = Field(200, ge=2, le=500)

    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')

    @field_validator('database_url')
    @classmethod
    def async_database_url(cls, value: str) -> str:
        for prefix in ('postgres://', 'postgresql://'):
            if value.startswith(prefix):
                value = value.replace(prefix, 'postgresql+asyncpg://', 1)
        if not value.startswith(('sqlite+aiosqlite:///', 'postgresql+asyncpg://')):
            raise ValueError('Use SQLite/aiosqlite or PostgreSQL/asyncpg')
        return value

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

    def validate_runtime(self) -> None:
        self.validate_llm_budget()
        if not self.bot_token.get_secret_value():
            raise RuntimeError('BOT_TOKEN is required')
        if not self.llm_api_key.get_secret_value():
            raise RuntimeError('LLM_API_KEY is required')
        if '*' in self.origins:
            raise RuntimeError('CORS_ORIGINS must list explicit origins')
        for origin in self.origins:
            parsed = urlparse(origin)
            if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise RuntimeError('Invalid CORS origin')
        if self.app_env == 'production':
            if not self.database_url.startswith('postgresql+asyncpg://'):
                raise RuntimeError('Production requires PostgreSQL')
            if not self.redis_url.get_secret_value():
                raise RuntimeError('Production requires REDIS_URL for shared generation limits')
            if not self.origins or any(not origin.startswith('https://') for origin in self.origins):
                raise RuntimeError('Production requires explicit HTTPS CORS origins')
            if not self.llm_api_url.startswith('https://'):
                raise RuntimeError('Production LLM_API_URL must use HTTPS')

    def validate_llm_budget(self) -> None:
        if self.llm_free_only:
            endpoint = urlparse(self.llm_api_url)
            if (endpoint.scheme != 'https' or endpoint.netloc != 'openrouter.ai'
                    or endpoint.path.rstrip('/') != '/api/v1'
                    or endpoint.query or endpoint.fragment):
                raise RuntimeError('LLM_FREE_ONLY requires the official OpenRouter HTTPS endpoint')
            if self.llm_model != 'openrouter/free' and not self.llm_model.endswith(':free'):
                raise RuntimeError('LLM_FREE_ONLY rejects paid models')


settings = Settings()
