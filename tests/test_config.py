import pytest

from rentals_assistant.config import ConfigError, load_config


def test_load_config_valid(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok_abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    config = load_config(_env_file=None)
    assert config.telegram_token == "tok_abc"
    assert config.telegram_chat_id == "999"
    assert config.price_min == 1400
    assert config.price_max == 2000
    assert config.enable_facebook is False
    assert config.log_level == "INFO"
    assert config.tz == "America/Toronto"


def test_load_config_custom_optionals(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok_abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("PRICE_MIN", "1200")
    monkeypatch.setenv("PRICE_MAX", "1800")
    monkeypatch.setenv("ENABLE_FACEBOOK", "true")
    config = load_config(_env_file=None)
    assert config.price_min == 1200
    assert config.price_max == 1800
    assert config.enable_facebook is True


def test_raises_config_error_missing_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    with pytest.raises(ConfigError):
        load_config(_env_file=None)


def test_raises_config_error_missing_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok_abc")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(ConfigError):
        load_config(_env_file=None)
