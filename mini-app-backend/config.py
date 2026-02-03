from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация Telegram Mini App."""

    # Telegram Bot (для валидации initData)
    bot_token: str = ""

    # LLM API
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.8

    # Database
    database_url: str = "sqlite+aiosqlite:///./hookah_app.db"

    # CORS
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Получить настройки приложения (кэшируется)."""
    return Settings()


settings = get_settings()
