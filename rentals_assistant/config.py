import logging

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
    max_concurrent_scrapers: int = 4


def load_config(**overrides) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def configure_logging(level: str) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        root.addHandler(handler)
