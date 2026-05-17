import logging

import pytest

from rentals_assistant.config import configure_logging, load_config


@pytest.fixture(autouse=True)
def reset_root_logger():
    """Remove all handlers added by configure_logging after each test."""
    root = logging.getLogger()
    before = set(root.handlers)
    yield
    after = set(root.handlers)
    for handler in after - before:
        root.removeHandler(handler)


def test_configure_logging_sets_level():
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_default_format():
    configure_logging("INFO")
    handler = logging.getLogger().handlers[-1]
    formatter = handler.formatter
    assert formatter._fmt == "%(asctime)s %(levelname)s %(name)s: %(message)s"


def test_configure_logging_no_duplicate_handlers():
    before = len(logging.getLogger().handlers)
    configure_logging("INFO")
    configure_logging("INFO")
    after = len(logging.getLogger().handlers)
    assert after == before


def test_log_level_from_env_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok_abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    config = load_config(_env_file=None)
    assert config.log_level == "DEBUG"


def test_debug_level_emits_debug_messages(caplog):
    configure_logging("DEBUG")
    logger = logging.getLogger("test_logger")
    logger.debug("debug message")
    assert "debug message" in caplog.text


def test_invalid_level_falls_back_to_info():
    configure_logging("INVALID")
    assert logging.getLogger().level == logging.INFO
