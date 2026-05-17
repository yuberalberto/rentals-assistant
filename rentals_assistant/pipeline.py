import hashlib
import logging

from rentals_assistant.filters import passes_hard_filters
from rentals_assistant.scorer import score_listing
from rentals_assistant.store import Store

logger = logging.getLogger(__name__)


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


async def run(scrapers, store: Store, notifier) -> None:
    """Scrape → filter → score → dedupe → notify.

    * Calls every scraper concurrently.
    * Hard-filter rejections are persisted with ``tier=None`` and
      ``notified=0`` for audit.
    * Passing listings are scored; only *new* ones trigger the notifier.
    * A scraper that raises is logged and skipped — the run never aborts.
    """
    all_listings = []

    for scraper in scrapers:
        try:
            listings = await scraper.fetch()
            all_listings.extend(listings)
        except Exception as exc:
            logger.error("Scraper %s failed: %s", type(scraper).__name__, exc)

    for listing in all_listings:
        listing_id = make_listing_id(listing.source, listing.external_id)
        is_new = store.is_new(listing_id)
        record = _listing_to_record(listing_id, listing)

        if not passes_hard_filters(listing):
            store.save({**record, "score": None, "tier": None, "notified": 0})
            continue

        result = score_listing(listing.__dict__)
        store.save({**record, "score": result.score, "tier": result.tier, "notified": 0})

        if is_new:
            sent = notifier(listing, result)
            if sent:
                store.mark_notified(listing_id)
