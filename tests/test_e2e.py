"""End-to-end test: real scrapers (mocked fetch) -> filters -> scorer -> store -> notifier."""
import json
from unittest.mock import AsyncMock

import pytest

from rentals_assistant.config import Settings
from rentals_assistant.pipeline import RunResult, make_listing_id, run
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper
from rentals_assistant.store import Store


# ---------------------------------------------------------------------------
# Fake JSON-embedded HTML payloads for RentalsCaScraper
# ---------------------------------------------------------------------------

def _node(
    listing_id: str,
    name: str,
    path: str,
    price: float,
    city_slug: str,
    beds: float = 2.0,
    baths: float = 1.0,
) -> dict:
    return {
        "node": {
            "__typename": "RentalListing",
            "id": listing_id,
            "path": path,
            "rentalListingName": name,
            "address": {
                "street": "123 Test St",
                "city": {
                    "__typename": "City",
                    "citySlug": city_slug,
                    "cityName": city_slug.title(),
                    "path": city_slug,
                    "regionCode": "ON",
                },
            },
            "rentRange": [price, price],
            "bedsRange": [beds, beds],
            "bathsRange": [baths, baths],
            "sizeRange": [900.0, 900.0],
        }
    }


def _embed_html(*edges: dict) -> str:
    data = {
        "data": {
            "meta": {"totalCount": len(edges)},
            "cities": [],
            "pageInfo": {"hasNextPage": False},
            "edges": list(edges),
        }
    }
    json_str = json.dumps(data)
    return f"""<html><body>
<script>
AppStartup.push(function() {{
  App.store.search = {{
    response: {json_str},
  }};
}});
</script>
</body></html>"""


# A listing that passes hard filters but scores CHECK (no proximity bonus)
_GOOD_NODE = _node(
    listing_id="good-001",
    name="Bright 2BR Upper Floor In-unit laundry Cats welcome",
    path="kitchener/bright-2br-upper-unit",
    price=1800.0,
    city_slug="kitchener",
)

# A listing that fails hard filter: basement unit (name triggers basement detection)
_BAD_BASEMENT_NODE = _node(
    listing_id="bad-001",
    name="Cozy Basement 2BR",
    path="kitchener/cozy-basement-2br",
    price=1500.0,
    city_slug="kitchener",
)

# A listing that fails hard filter: price too high
_BAD_PRICE_NODE = _node(
    listing_id="bad-002",
    name="Luxury 2BR Penthouse",
    path="waterloo/luxury-2br",
    price=3500.0,
    city_slug="waterloo",
)

# Second good listing from Cambridge (scores STRONG: proximity + main floor + pets + bathrooms)
_GOOD_NODE_2 = _node(
    listing_id="good-002",
    name="Spacious 2BR Main Floor In-unit laundry Cats confirmed Patio 2 parking spots",
    path="cambridge/spacious-2br",
    price=1700.0,
    city_slug="cambridge",
    baths=1.5,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "e2e_test.db")
    yield s
    s.close()


@pytest.fixture
def settings():
    return Settings(
        telegram_token="fake-token",
        telegram_chat_id="fake-chat-id",
        max_concurrent_scrapers=4,
        min_notify_tier="strong",
    )


# ---------------------------------------------------------------------------
# Helper: create a scraper with a mock _fetch that returns city-specific HTML
# ---------------------------------------------------------------------------

def _make_scraper(city_html: dict[str, str]) -> RentalsCaScraper:
    """Create a RentalsCaScraper with a mock fetch function."""

    async def fake_fetch(url, **kwargs):
        for city, html in city_html.items():
            if city in url:
                return html
        return "<html><body></body></html>"

    return RentalsCaScraper(_fetch=fake_fetch)


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_full_pipeline_with_real_scraper(store, settings):
    """Full pipeline: real scraper parsing HTML -> filters -> scorer -> store -> notify."""
    scraper = _make_scraper({
        "kitchener": _embed_html(_GOOD_NODE, _BAD_BASEMENT_NODE),
        "waterloo": _embed_html(_BAD_PRICE_NODE),
        "cambridge": _embed_html(_GOOD_NODE_2),
    })

    notifier = AsyncMock(return_value=True)
    result = await run([scraper], store, notifier=notifier, settings=settings)

    assert isinstance(result, RunResult)
    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 0
    assert result.listings_found == 4
    assert result.listings_rejected == 2  # basement + overpriced
    assert result.listings_new == 1  # only Cambridge passes tier gate
    assert result.listings_notified == 1

    assert notifier.call_count == 1

    # Verify Kitchener listing (CHECK tier) is saved but not notified
    kitchener_id = make_listing_id("rentals_ca", "good-001")
    cur = store._conn.execute(
        "SELECT score, tier, notified FROM listings WHERE id = ?", (kitchener_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] is not None
    assert row[1] == "check"
    assert row[2] == 0

    # Verify Cambridge listing (STRONG tier) is saved and notified
    cambridge_id = make_listing_id("rentals_ca", "good-002")
    cur = store._conn.execute(
        "SELECT score, tier, notified FROM listings WHERE id = ?", (cambridge_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] is not None
    assert row[1] == "strong"
    assert row[2] == 1

    # Verify rejected listings stored with tier=None
    bad_id = make_listing_id("rentals_ca", "bad-001")
    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (bad_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] == 0


@pytest.mark.asyncio
async def test_e2e_deduplication_on_second_run(store, settings):
    """Second run with same listings should NOT re-notify."""
    city_html = {
        "kitchener": _embed_html(),
        "waterloo": _embed_html(),
        "cambridge": _embed_html(_GOOD_NODE_2),
    }

    notifier = AsyncMock(return_value=True)

    # First run
    result1 = await run([_make_scraper(city_html)], store, notifier=notifier, settings=settings)
    assert result1.listings_notified == 1

    # Second run — same listing, should be deduped
    notifier.reset_mock()
    result2 = await run([_make_scraper(city_html)], store, notifier=notifier, settings=settings)

    assert result2.listings_found == 1
    assert result2.listings_new == 0
    assert result2.listings_notified == 0
    assert notifier.call_count == 0


@pytest.mark.asyncio
async def test_e2e_scraper_failure_plus_success(store, settings):
    """One scraper fails, another succeeds — pipeline continues and reports both."""
    good_scraper = _make_scraper({
        "kitchener": _embed_html(),
        "waterloo": _embed_html(),
        "cambridge": _embed_html(_GOOD_NODE_2),
    })

    # Failing scraper — uses a Scraper subclass that raises on fetch
    from rentals_assistant.scrapers.base import Scraper

    class FailingScraper(Scraper):
        async def fetch(self):
            raise Exception("Scraper down")

    fail_scraper = FailingScraper()

    notifier = AsyncMock(return_value=True)
    result = await run(
        [fail_scraper, good_scraper], store, notifier=notifier, settings=settings
    )

    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 1
    assert result.listings_found == 1
    assert result.listings_notified == 1


@pytest.mark.asyncio
async def test_e2e_empty_scrape_produces_zero_result(store, settings):
    """Scraper finds no listings — RunResult all zeros except scrapers_ok."""
    scraper = _make_scraper({
        "kitchener": _embed_html(),
        "waterloo": _embed_html(),
        "cambridge": _embed_html(),
    })
    notifier = AsyncMock(return_value=True)
    result = await run([scraper], store, notifier=notifier, settings=settings)

    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 0
    assert result.listings_found == 0
    assert result.listings_new == 0
    assert result.listings_notified == 0
    assert result.listings_rejected == 0
