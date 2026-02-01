from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация Telegram бота с кастомным LLM API."""

    # Telegram Bot
    bot_token: str
    admin_id: int

    # LLM API (опционально)
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 1000
    llm_temperature: float = 0.8

    # Database
    database_url: str = "sqlite+aiosqlite:///./hookah_bot.db"

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
