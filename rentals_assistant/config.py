from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_token: str
    telegram_chat_id: str
    price_min: int = 1400
    price_max: int = 2000
    enable_facebook: bool = False
    log_level: str = "INFO"
    tz: str = "America/Toronto"


def load_config(**overrides) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
