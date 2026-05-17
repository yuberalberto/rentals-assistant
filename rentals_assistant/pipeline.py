import asyncio
import hashlib
import logging
from dataclasses import dataclass

from rentals_assistant.filters import passes_hard_filters
from rentals_assistant.scorer import score_listing
from rentals_assistant.store import Store

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    scrapers_ok: int = 0
    scrapers_failed: int = 0
    listings_found: int = 0
    listings_new: int = 0
    listings_notified: int = 0
    listings_rejected: int = 0


def make_listing_id(source: str, external_id: str) -> str:
    return hashlib.sha256(f"{source}{external_id}".encode()).hexdigest()


def _listing_to_record(listing_id: str, listing) -> dict:
    return {
        "id": listing_id,
        "source": listing.source,
        "external_id": listing.external_id,
        "url": listing.url,
        "title": listing.title,
        "price_cad": listing.price_cad,
        "utilities": listing.utilities,
        "bedrooms": listing.bedrooms,
        "city": listing.city,
        "floor_level": listing.floor_level,
        "laundry_inunit": listing.laundry_inunit,
        "outdoor_space": listing.outdoor_space,
        "parking_spots": listing.parking_spots,
        "pets": listing.pets,
    }


async def run(scrapers, store: Store, notifier, settings=None) -> RunResult:
    """Scrape → filter → score → dedupe → notify.

    * Calls every scraper concurrently.
    * Hard-filter rejections are persisted with ``tier=None`` and
      ``notified=0`` for audit.
    * Passing listings are scored; only *new* ones trigger the notifier.
    * A scraper that raises is logged and skipped — the run never aborts.
    """
    if settings is None:
        from rentals_assistant.config import Settings
        settings = Settings()

    semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)

    async def fetch_with_semaphore(scraper):
        async with semaphore:
            try:
                listings = await scraper.fetch()
                return listings, True
            except Exception as exc:
                logger.error("Scraper %s failed: %s", type(scraper).__name__, exc)
                return [], False

    results = await asyncio.gather(*[fetch_with_semaphore(scraper) for scraper in scrapers])

    scrapers_ok = sum(1 for _, ok in results if ok)
    scrapers_failed = sum(1 for _, ok in results if not ok)

    all_listings = []
    for listings, _ in results:
        all_listings.extend(listings)

    listings_found = len(all_listings)
    listings_new = 0
    listings_notified = 0
    listings_rejected = 0

    for listing in all_listings:
        listing_id = make_listing_id(listing.source, listing.external_id)
        is_new = store.is_new(listing_id)
        record = _listing_to_record(listing_id, listing)

        if not passes_hard_filters(listing):
            store.save({**record, "score": None, "tier": None, "notified": 0})
            listings_rejected += 1
            continue

        result = score_listing(listing.__dict__)
        store.save({**record, "score": result.score, "tier": result.tier, "notified": 0})

        if is_new:
            listings_new += 1
            sent = await notifier(listing, result)
            if sent:
                store.mark_notified(listing_id)
                listings_notified += 1

    return RunResult(
        scrapers_ok=scrapers_ok,
        scrapers_failed=scrapers_failed,
        listings_found=listings_found,
        listings_new=listings_new,
        listings_notified=listings_notified,
        listings_rejected=listings_rejected,
    )
