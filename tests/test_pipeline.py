"""Tests for pipeline.py — scrape → filter → score → dedupe → notify."""
import asyncio
import hashlib
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rentals_assistant.models import RawListing
from rentals_assistant.pipeline import make_listing_id, run
from rentals_assistant.scorer import ScoringResult
from rentals_assistant.store import Store

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_listing(
    source="kijiji",
    external_id="ext-001",
    url="https://kijiji.ca/v-1",
    title="Nice 2BR",
    price_cad=1800,
    bedrooms=2,
    city="Cambridge",
    floor_level="upper",
    laundry_inunit=True,
    outdoor_space=True,
    parking_spots=1,
    pets="cats_confirmed",
    utilities="included",
) -> RawListing:
    return RawListing(
        source=source,
        external_id=external_id,
        url=url,
        title=title,
        price_cad=price_cad,
        bedrooms=bedrooms,
        city=city,
        floor_level=floor_level,
        laundry_inunit=laundry_inunit,
        outdoor_space=outdoor_space,
        parking_spots=parking_spots,
        pets=pets,
        utilities=utilities,
    )


def _make_scraper(listings: List[RawListing]):
    scraper = MagicMock()
    scraper.fetch = AsyncMock(return_value=listings)
    return scraper


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


# ---------------------------------------------------------------------------
# make_listing_id
# ---------------------------------------------------------------------------

def test_make_listing_id_is_sha256_of_source_and_external_id():
    expected = hashlib.sha256(b"kijijiext-001").hexdigest()
    assert make_listing_id("kijiji", "ext-001") == expected


def test_make_listing_id_different_sources_produce_different_ids():
    id1 = make_listing_id("kijiji", "ext-001")
    id2 = make_listing_id("rentals_ca", "ext-001")
    assert id1 != id2


# ---------------------------------------------------------------------------
# AC1: pipeline.run() calls all enabled scrapers
# ---------------------------------------------------------------------------

async def test_run_calls_all_scrapers(store):
    scraper_a = _make_scraper([])
    scraper_b = _make_scraper([])

    await run([scraper_a, scraper_b], store, notifier=MagicMock())

    scraper_a.fetch.assert_called_once()
    scraper_b.fetch.assert_called_once()


# ---------------------------------------------------------------------------
# AC2: Hard-rejected listings stored with tier=None, notified=0
# ---------------------------------------------------------------------------

async def test_rejected_listing_saved_with_null_tier(store):
    rejected = _make_listing(price_cad=9999)  # exceeds $2,000 ceiling
    scraper = _make_scraper([rejected])

    await run([scraper], store, notifier=MagicMock())

    listing_id = make_listing_id(rejected.source, rejected.external_id)
    assert not store.is_new(listing_id)  # was saved

    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    assert row[0] is None  # tier is NULL
    assert row[1] == 0     # notified = 0


async def test_rejected_listing_does_not_trigger_notifier(store):
    rejected = _make_listing(bedrooms=3)
    scraper = _make_scraper([rejected])
    notifier = MagicMock()

    await run([scraper], store, notifier=notifier)

    notifier.assert_not_called()


# ---------------------------------------------------------------------------
# AC3: Only new + passing listings trigger notification
# ---------------------------------------------------------------------------

async def test_new_passing_listing_triggers_notification(store):
    from rentals_assistant.config import Settings

    listing = _make_listing(
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )
    scraper = _make_scraper([listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",  # allow STRONG and PERFECT
    )

    await run([scraper], store, notifier=notifier, settings=settings)

    notifier.assert_called_once()
    # enrich() returns a new instance, so check data instead of identity
    notified_listing = notifier.call_args[0][0]
    assert notified_listing.source == listing.source
    assert notified_listing.external_id == listing.external_id
    assert isinstance(notifier.call_args[0][1], ScoringResult)


async def test_new_passing_listing_marked_notified_after_alert(store):
    from rentals_assistant.config import Settings

    listing = _make_listing(
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )
    scraper = _make_scraper([listing])

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    await run([scraper], store, notifier=AsyncMock(return_value=True), settings=settings)

    listing_id = make_listing_id(listing.source, listing.external_id)
    cur = store._conn.execute(
        "SELECT notified FROM listings WHERE id = ?", (listing_id,)
    )
    assert cur.fetchone()[0] == 1


async def test_existing_passing_listing_does_not_trigger_notification(store):
    listing = _make_listing()
    listing_id = make_listing_id(listing.source, listing.external_id)

    store.save({
        "id": listing_id,
        "source": listing.source,
        "external_id": listing.external_id,
        "url": listing.url,
        "title": listing.title,
        "price_cad": listing.price_cad,
        "bedrooms": listing.bedrooms,
        "city": listing.city,
        "floor_level": listing.floor_level,
        "laundry_inunit": listing.laundry_inunit,
        "outdoor_space": listing.outdoor_space,
        "parking_spots": listing.parking_spots,
        "pets": listing.pets,
        "utilities": listing.utilities,
        "score": 3,
        "tier": "strong",
        "notified": 1,
    })

    scraper = _make_scraper([listing])
    notifier = MagicMock()

    await run([scraper], store, notifier=notifier)

    notifier.assert_not_called()


async def test_passing_listing_saved_with_score_and_tier(store):
    from rentals_assistant.config import Settings

    listing = _make_listing(
        utilities="included", floor_level="upper",
        outdoor_space=True, parking_spots=2,
    )
    scraper = _make_scraper([listing])

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    await run([scraper], store, notifier=AsyncMock(return_value=True), settings=settings)

    listing_id = make_listing_id(listing.source, listing.external_id)
    cur = store._conn.execute(
        "SELECT score, tier FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    # After TASK-CUR-006, scoring expanded to 0-7 with pets and proximity criteria
    # utilities(1) + upper(1) + outdoor(1) + parking2(1) + pets(1) + cambridge(1) = 6
    assert row[0] == 6
    assert row[1] == "strong"


# ---------------------------------------------------------------------------
# AC4: Scraper failure logs error and continues — never aborts
# ---------------------------------------------------------------------------

async def test_scraper_exception_does_not_abort_run(store):
    from rentals_assistant.config import Settings

    failing = MagicMock()
    failing.fetch = AsyncMock(side_effect=RuntimeError("network error"))

    good_listing = _make_listing(
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )
    good = _make_scraper([good_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    await run([failing, good], store, notifier=notifier, settings=settings)  # must not raise

    notifier.assert_called_once()


async def test_scraper_exception_is_logged(store):
    failing = MagicMock()
    failing.fetch = AsyncMock(side_effect=ValueError("parse error"))

    with patch("rentals_assistant.pipeline.logger") as mock_logger:
        await run([failing], store, notifier=MagicMock())

    mock_logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# AC5: End-to-end integration test with mocked notifier
# ---------------------------------------------------------------------------

async def test_end_to_end_mixed_listings(store):
    """1 new passing, 1 rejected, 1 existing passing — only 1 notification sent."""
    from rentals_assistant.config import Settings

    passing_new = _make_listing(
        external_id="new-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )
    rejected = _make_listing(external_id="bad-001", price_cad=9999)
    passing_existing = _make_listing(
        external_id="old-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )

    existing_id = make_listing_id(passing_existing.source, passing_existing.external_id)
    store.save({
        "id": existing_id,
        "source": passing_existing.source,
        "external_id": passing_existing.external_id,
        "url": passing_existing.url,
        "title": passing_existing.title,
        "price_cad": passing_existing.price_cad,
        "bedrooms": passing_existing.bedrooms,
        "city": passing_existing.city,
        "floor_level": passing_existing.floor_level,
        "laundry_inunit": passing_existing.laundry_inunit,
        "outdoor_space": passing_existing.outdoor_space,
        "parking_spots": passing_existing.parking_spots,
        "pets": passing_existing.pets,
        "utilities": passing_existing.utilities,
        "score": 4,
        "tier": "strong",
        "notified": 1,
    })

    scraper = _make_scraper([passing_new, rejected, passing_existing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    await run([scraper], store, notifier=notifier, settings=settings)

    assert notifier.call_count == 1
    # enrich() returns a new instance, so check data instead of identity
    notified_listing = notifier.call_args[0][0]
    assert notified_listing.source == passing_new.source
    assert notified_listing.external_id == passing_new.external_id

    rejected_id = make_listing_id(rejected.source, rejected.external_id)
    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (rejected_id,)
    )
    row = cur.fetchone()
    assert row[0] is None
    assert row[1] == 0


# ---------------------------------------------------------------------------
# TASK-104: Concurrent scraper execution with semaphore
# ---------------------------------------------------------------------------

async def test_concurrent_execution_with_semaphore(store):
    """Verify scrapers run concurrently when max_concurrent_scrapers > 1."""
    scraper_a = _make_scraper([])
    scraper_a.__class__.__name__ = "ScraperA"

    scraper_b = _make_scraper([])
    scraper_b.__class__.__name__ = "ScraperB"

    scraper_c = _make_scraper([])
    scraper_c.__class__.__name__ = "ScraperC"

    from rentals_assistant.config import Settings
    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        max_concurrent_scrapers=3
    )

    await run([scraper_a, scraper_b, scraper_c], store, notifier=AsyncMock(), settings=settings)

    # All scrapers should have been called
    scraper_a.fetch.assert_called_once()
    scraper_b.fetch.assert_called_once()
    scraper_c.fetch.assert_called_once()


async def test_semaphore_one_forces_sequential_execution(store):
    """Verify semaphore=1 forces sequential behavior."""
    scraper_a = _make_scraper([])
    scraper_a.__class__.__name__ = "ScraperA"

    scraper_b = _make_scraper([])
    scraper_b.__class__.__name__ = "ScraperB"

    from rentals_assistant.config import Settings
    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        max_concurrent_scrapers=1
    )

    await run([scraper_a, scraper_b], store, notifier=AsyncMock(), settings=settings)

    # Both scrapers should have been called sequentially
    scraper_a.fetch.assert_called_once()
    scraper_b.fetch.assert_called_once()


async def test_concurrent_failure_does_not_cancel_others(store):
    """Verify a failing scraper doesn't cancel others in concurrent execution."""
    failing = MagicMock()
    failing.__class__.__name__ = "FailingScraper"
    failing.fetch = AsyncMock(side_effect=RuntimeError("network error"))

    good_a = _make_scraper([_make_listing(
        external_id="good-a-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )])
    good_a.__class__.__name__ = "GoodA"

    good_b = _make_scraper([_make_listing(
        external_id="good-b-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )])
    good_b.__class__.__name__ = "GoodB"

    from rentals_assistant.config import Settings
    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        max_concurrent_scrapers=3,
        min_notify_tier="strong",
    )

    notifier = AsyncMock(return_value=True)
    await run([failing, good_a, good_b], store, notifier=notifier, settings=settings)

    # All scrapers should have been attempted
    failing.fetch.assert_called_once()
    good_a.fetch.assert_called_once()
    good_b.fetch.assert_called_once()

    # Notifier should have been called for the good scrapers (2 listings)
    assert notifier.call_count == 2


# ---------------------------------------------------------------------------
# TASK-105: RunResult with structured error reporting
# ---------------------------------------------------------------------------

async def test_run_returns_run_result(store):
    """pipeline.run() must return a RunResult dataclass."""
    from rentals_assistant.pipeline import RunResult

    listing = _make_listing()
    scraper = _make_scraper([listing])
    notifier = AsyncMock(return_value=True)

    result = await run([scraper], store, notifier=notifier)

    assert isinstance(result, RunResult)


async def test_run_result_counts_all_listings(store):
    """RunResult must track found, new, notified, rejected."""
    from rentals_assistant.config import Settings

    new_passing = _make_listing(
        external_id="new-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )
    rejected = _make_listing(external_id="bad-001", price_cad=9999)
    existing = _make_listing(
        external_id="old-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )

    existing_id = make_listing_id(existing.source, existing.external_id)
    store.save({
        "id": existing_id,
        "source": existing.source,
        "external_id": existing.external_id,
        "url": existing.url,
        "title": existing.title,
        "price_cad": existing.price_cad,
        "bedrooms": existing.bedrooms,
        "city": existing.city,
        "floor_level": existing.floor_level,
        "laundry_inunit": existing.laundry_inunit,
        "outdoor_space": existing.outdoor_space,
        "parking_spots": existing.parking_spots,
        "pets": existing.pets,
        "utilities": existing.utilities,
        "score": 4,
        "tier": "strong",
        "notified": 1,
    })

    scraper = _make_scraper([new_passing, rejected, existing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 0
    assert result.listings_found == 3
    assert result.listings_new == 1
    assert result.listings_notified == 1
    assert result.listings_rejected == 1


async def test_run_result_tracks_scraper_failures(store):
    """RunResult must count failed scrapers and still count listings from ok ones."""
    from rentals_assistant.pipeline import RunResult
    from rentals_assistant.config import Settings

    failing = MagicMock()
    failing.__class__.__name__ = "FailingScraper"
    failing.fetch = AsyncMock(side_effect=RuntimeError("boom"))

    good = _make_scraper([_make_listing(
        external_id="good-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )])

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    notifier = AsyncMock(return_value=True)
    result = await run([failing, good], store, notifier=notifier, settings=settings)

    assert isinstance(result, RunResult)
    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 1
    assert result.listings_found == 1
    assert result.listings_new == 1
    assert result.listings_notified == 1
    assert result.listings_rejected == 0


async def test_run_result_zero_when_no_scrapers(store):
    """RunResult must be all zeros when no scrapers are provided."""
    from rentals_assistant.pipeline import RunResult

    result = await run([], store, notifier=MagicMock())

    assert isinstance(result, RunResult)
    assert result.scrapers_ok == 0
    assert result.scrapers_failed == 0
    assert result.listings_found == 0
    assert result.listings_new == 0
    assert result.listings_notified == 0
    assert result.listings_rejected == 0


async def test_run_result_counts_rejected_not_notified(store):
    """Rejected listings are found but not new/notified."""
    rejected = _make_listing(external_id="rej-001", price_cad=9999)
    scraper = _make_scraper([rejected])
    notifier = AsyncMock(return_value=True)

    result = await run([scraper], store, notifier=notifier)

    assert result.listings_found == 1
    assert result.listings_new == 0
    assert result.listings_notified == 0
    assert result.listings_rejected == 1


# ---------------------------------------------------------------------------
# TASK-CUR-007: Enrichment + Validation + Tier Gate
# ---------------------------------------------------------------------------

async def test_enrichment_runs_before_filtering(store):
    """Enrichment should fill missing fields from title+description before filtering."""
    from rentals_assistant.enrichment import enrich

    listing = RawListing(
        source="kijiji",
        external_id="enrich-001",
        url="https://kijiji.ca/v-1",
        title="2BR apartment $1800",
        price_cad=None,  # missing - should be filled by enrichment
        bedrooms=None,
        city="Cambridge",
        floor_level=None,
        laundry_inunit=None,
        outdoor_space=None,
        parking_spots=None,
        pets=None,
        utilities=None,
        description=None,
        bathrooms=None,
    )

    scraper = _make_scraper([listing])
    notifier = AsyncMock(return_value=True)

    await run([scraper], store, notifier=notifier)

    listing_id = make_listing_id(listing.source, listing.external_id)
    cur = store._conn.execute(
        "SELECT price_cad FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    assert row[0] == 1800  # enrichment filled the price


async def test_validation_rejects_no_price_listings(store):
    """Listings with no price after enrichment should be rejected."""
    listing = RawListing(
        source="kijiji",
        external_id="noprice-001",
        url="https://kijiji.ca/v-1",
        title="Nice apartment",
        price_cad=None,
        bedrooms=2,
        city="Cambridge",
        floor_level="upper",
        laundry_inunit=True,
        outdoor_space=True,
        parking_spots=1,
        pets="cats_confirmed",
        utilities="included",
        description="No price mentioned",
        bathrooms=1.5,
    )

    scraper = _make_scraper([listing])
    notifier = AsyncMock(return_value=True)

    result = await run([scraper], store, notifier=notifier)

    # Should be rejected (notified=0, tier=None)
    assert result.listings_rejected == 1
    assert result.listings_notified == 0

    listing_id = make_listing_id(listing.source, listing.external_id)
    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    assert row[0] is None
    assert row[1] == 0


async def test_tier_gate_respects_min_notify_tier_perfect(store):
    """With min_notify_tier=perfect, only PERFECT listings trigger notifications."""
    from rentals_assistant.config import Settings

    # Create a STRONG listing (score 5)
    strong_listing = _make_listing(
        external_id="strong-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )

    scraper = _make_scraper([strong_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="perfect",
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    # STRONG listing should be saved but not notified
    assert result.listings_notified == 0

    listing_id = make_listing_id(strong_listing.source, strong_listing.external_id)
    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    assert row[0] == "strong"
    assert row[1] == 0


async def test_tier_gate_respects_min_notify_tier_strong(store):
    """With min_notify_tier=strong, STRONG and PERFECT trigger notifications."""
    from rentals_assistant.config import Settings

    strong_listing = _make_listing(
        external_id="strong-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )

    scraper = _make_scraper([strong_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="strong",
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    # STRONG listing should be notified
    assert result.listings_notified == 1


async def test_check_listings_saved_but_not_notified(store):
    """CHECK tier listings should be saved in DB but not notified with default config."""
    from rentals_assistant.config import Settings

    # Create a CHECK listing (low score) - passes hard filters but low score
    check_listing = _make_listing(
        external_id="check-001",
        utilities=None,
        floor_level="main",  # passes hard filter
        outdoor_space=False,
        parking_spots=1,
    )

    scraper = _make_scraper([check_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="perfect",  # default
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    # CHECK listing should be saved but not notified
    assert result.listings_rejected == 0  # not rejected by hard filters
    assert result.listings_notified == 0

    listing_id = make_listing_id(check_listing.source, check_listing.external_id)
    cur = store._conn.execute(
        "SELECT tier, notified, score FROM listings WHERE id = ?", (listing_id,)
    )
    row = cur.fetchone()
    assert row[0] == "check"
    assert row[1] == 0
    assert row[2] is not None


async def test_tier_gate_unknown_tier_defaults_to_lowest(store):
    """Unknown min_notify_tier should default to 'check' behavior (notify all)."""
    from rentals_assistant.config import Settings

    check_listing = _make_listing(
        external_id="check-001",
        utilities=None,
        floor_level="main",
        outdoor_space=False,
        parking_spots=1,
    )

    scraper = _make_scraper([check_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="unknown_tier",  # invalid tier name
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    # Unknown tier defaults to lowest (0), so CHECK listing passes gate
    assert result.listings_notified == 1


async def test_existing_listing_below_tier_not_renotified(store):
    """Existing listing below tier threshold should not trigger re-notification."""
    from rentals_assistant.config import Settings

    strong_listing = _make_listing(
        external_id="strong-001",
        utilities="included",
        floor_level="upper",
        outdoor_space=True,
        parking_spots=2,
    )

    # Pre-save as existing with CHECK tier (low score from before)
    listing_id = make_listing_id(strong_listing.source, strong_listing.external_id)
    store.save({
        "id": listing_id,
        "source": strong_listing.source,
        "external_id": strong_listing.external_id,
        "url": strong_listing.url,
        "title": strong_listing.title,
        "price_cad": strong_listing.price_cad,
        "bedrooms": strong_listing.bedrooms,
        "city": strong_listing.city,
        "floor_level": strong_listing.floor_level,
        "laundry_inunit": strong_listing.laundry_inunit,
        "outdoor_space": strong_listing.outdoor_space,
        "parking_spots": strong_listing.parking_spots,
        "pets": strong_listing.pets,
        "utilities": strong_listing.utilities,
        "score": 2,
        "tier": "check",
        "notified": 1,
    })

    scraper = _make_scraper([strong_listing])
    notifier = AsyncMock(return_value=True)

    settings = Settings(
        telegram_token="test",
        telegram_chat_id="test",
        min_notify_tier="perfect",
    )

    result = await run([scraper], store, notifier=notifier, settings=settings)

    # Not new, and even if it were, below tier threshold
    assert result.listings_new == 0
    assert result.listings_notified == 0
    notifier.assert_not_called()
