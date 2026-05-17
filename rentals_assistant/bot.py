import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from rentals_assistant import pipeline
from rentals_assistant.config import load_config
from rentals_assistant.notifier import send_alert
from rentals_assistant.store import Store

logger = logging.getLogger(__name__)
_pipeline_lock = asyncio.Lock()


async def _handle_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_config()
    if update.effective_chat.id != int(config.telegram_chat_id):
        return

    if _pipeline_lock.locked():
        await update.message.reply_text("Already scanning, please wait ⏳")
        return

    await update.message.reply_text("Scanning... 🔍")
    async with _pipeline_lock:
        store = Store("listings.db")
        await pipeline.run(scrapers=[], store=store, notifier=send_alert)


def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("run", _handle_run))
    return app


def start_bot() -> None:
    config = load_config()
    build_application(config.telegram_token).run_polling()
