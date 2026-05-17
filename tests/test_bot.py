from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rentals_assistant import bot as bot_module
from rentals_assistant.bot import _handle_run, build_application


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.telegram_chat_id = "12345"
    cfg.telegram_token = "fake-token"
    return cfg


@pytest.fixture
def authorized_update():
    upd = MagicMock()
    upd.effective_chat.id = 12345
    upd.message.reply_text = AsyncMock()
    return upd


@pytest.fixture
def unauthorized_update():
    upd = MagicMock()
    upd.effective_chat.id = 99999
    upd.message.reply_text = AsyncMock()
    return upd


@pytest.fixture
def mock_context():
    return MagicMock()


class TestHandleRun:
    @patch("rentals_assistant.bot.load_config")
    @patch("rentals_assistant.bot.pipeline.run", new_callable=AsyncMock)
    async def test_unauthorized_chat_id_is_ignored(
        self, mock_pipeline_run, mock_load_config, unauthorized_update, mock_context, mock_config
    ):
        mock_load_config.return_value = mock_config

        await _handle_run(unauthorized_update, mock_context)

        mock_pipeline_run.assert_not_called()
        unauthorized_update.message.reply_text.assert_not_called()

    @patch("rentals_assistant.bot.load_config")
    @patch("rentals_assistant.bot.pipeline.run", new_callable=AsyncMock)
    async def test_authorized_chat_id_triggers_pipeline(
        self, mock_pipeline_run, mock_load_config, authorized_update, mock_context, mock_config
    ):
        mock_load_config.return_value = mock_config

        await _handle_run(authorized_update, mock_context)

        mock_pipeline_run.assert_awaited_once()
        authorized_update.message.reply_text.assert_awaited_once_with("Scanning... 🔍")

    @patch("rentals_assistant.bot.load_config")
    @patch("rentals_assistant.bot.pipeline.run", new_callable=AsyncMock)
    async def test_double_run_returns_busy_message(
        self, mock_pipeline_run, mock_load_config, authorized_update, mock_context, mock_config
    ):
        mock_load_config.return_value = mock_config

        lock = bot_module._pipeline_lock
        async with lock:
            await _handle_run(authorized_update, mock_context)

        mock_pipeline_run.assert_not_called()
        authorized_update.message.reply_text.assert_awaited_once_with(
            "Already scanning, please wait ⏳"
        )


class TestBuildApplication:
    @patch("rentals_assistant.bot.Application.builder")
    def test_adds_run_handler(self, mock_builder):
        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app

        result = build_application("tok")

        assert result is mock_app
        mock_app.add_handler.assert_called_once()
        handler = mock_app.add_handler.call_args[0][0]
        assert handler.callback is _handle_run
