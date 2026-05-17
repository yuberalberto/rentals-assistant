"""Tests for scheduler.py — APScheduler wiring."""
from unittest.mock import AsyncMock, MagicMock, patch

from apscheduler.triggers.cron import CronTrigger

from rentals_assistant.scheduler import build_scheduler, log_next_fire_times

# ---------------------------------------------------------------------------
# RED phase — all fail until scheduler.py exists
# ---------------------------------------------------------------------------


def test_registers_three_jobs():
    config = MagicMock(tz="America/Toronto")
    scheduler = build_scheduler(config, [], MagicMock(), MagicMock())
    jobs = scheduler.get_jobs()
    assert len(jobs) == 3


def test_job_hours():
    config = MagicMock(tz="America/Toronto")
    scheduler = build_scheduler(config, [], MagicMock(), MagicMock())
    jobs = scheduler.get_jobs()
    hours = set()
    for job in jobs:
        assert isinstance(job.trigger, CronTrigger)
        hour_field = next(f for f in job.trigger.fields if f.name == "hour")
        hours.add(hour_field.expressions[0].first)
    assert hours == {8, 13, 18}


def test_timezone_is_toronto():
    config = MagicMock(tz="America/Toronto")
    scheduler = build_scheduler(config, [], MagicMock(), MagicMock())
    assert str(scheduler.timezone) == "America/Toronto"


def test_timezone_from_config():
    config = MagicMock(tz="UTC")
    scheduler = build_scheduler(config, [], MagicMock(), MagicMock())
    assert str(scheduler.timezone) == "UTC"


async def test_run_wrapper_calls_pipeline():
    config = MagicMock(tz="America/Toronto")
    scrapers = [MagicMock()]
    store = MagicMock()
    notifier = MagicMock()

    with patch("rentals_assistant.scheduler.pipeline") as mock_pipeline:
        mock_pipeline.run = AsyncMock()
        scheduler = build_scheduler(config, scrapers, store, notifier)
        job = scheduler.get_jobs()[0]
        await job.func(*job.args)
        mock_pipeline.run.assert_awaited_once_with(scrapers, store, notifier)


async def test_log_next_fire_time():
    config = MagicMock(tz="America/Toronto")
    scheduler = build_scheduler(config, [], MagicMock(), MagicMock())
    scheduler.start()
    try:
        with patch("rentals_assistant.scheduler.logger") as mock_logger:
            log_next_fire_times(scheduler)
            assert mock_logger.info.call_count == 3
    finally:
        scheduler.shutdown(wait=False)
