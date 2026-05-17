import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from rentals_assistant import pipeline
from rentals_assistant.config import load_config
from rentals_assistant.notifier import send_alert, send_summary
from rentals_assistant.scrapers import build_scrapers
from rentals_assistant.store import Store

logger = logging.getLogger(__name__)


async def _run_pipeline(scrapers, store, notifier) -> None:
    result = await pipeline.run(scrapers, store, notifier)
    await send_summary(result)


def build_scheduler(config, scrapers, store, notifier) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=config.tz)
    for hour in (8, 13, 18):
        scheduler.add_job(
            _run_pipeline,
            trigger=CronTrigger(hour=hour, minute=0),
            id=f"scrape-{hour:02d}",
            args=[scrapers, store, notifier],
        )
    return scheduler


def log_next_fire_times(scheduler) -> None:
    for job in scheduler.get_jobs():
        logger.info("Next run: %s", job.next_run_time)


def start() -> None:
    config = load_config()
    scrapers = build_scrapers()
    store = Store("listings.db")
    scheduler = build_scheduler(config, scrapers, store, send_alert)
    log_next_fire_times(scheduler)
    scheduler.start()
    asyncio.get_event_loop().run_forever()
