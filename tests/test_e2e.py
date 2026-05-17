"""End-to-end test: real scrapers (mocked HTTP) → filters → scorer → store → notifier."""
import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from rentals_assistant.config import Settings
from rentals_assistant.models import RawListing
from rentals_assistant.pipeline import RunResult, make_listing_id, run
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper
from rentals_assistant.store import Store


# ---------------------------------------------------------------------------
# Fake HTML payloads for RentalsCaScraper
# ---------------------------------------------------------------------------

def _listing_card(
    listing_id: str,
    title: str,
    href: str,
    price: str,
    beds: str,
    description: str,
) -> str:
    return f"""
    <article class="listing-card" data-listing-id="{listing_id}">
        <a class="listing-card__title" href="{href}">{title}</a>
        <span class="listing-card__price">{price}</span>
        <span class="listing-card__beds">{beds}</span>
        <div class="listing-card__description">{description}</div>
    </article>
    """


# A listing that passes all hard filters: 2BR, $1800, cats, in-unit laundry, not basement
_GOOD_CARD = _listing_card(
    listing_id="good-001",
    title="Bright 2BR Upper Unit",
    href="/kitchener/bright-2br-upper-unit-12345",
    price="$1,800/mo utilities included",
    beds="2 beds",
    description="Upper floor. In-unit laundry. Cats welcome. Balcony. 1 parking spot.",
)

# A listing that fails hard filter: basement unit
_BAD_BASEMENT = _listing_card(
    listing_id="bad-001",
    title="Cozy Basement 2BR",
    href="/kitchener/cozy-basement-2br-67890",
    price="$1,500/mo",
    beds="2 beds",
    description="Basement unit. Laundry in-unit. Cats allowed. 1 parking.",
)

# A listing that fails hard filter: price too high
_BAD_PRICE = _listing_card(
    listing_id="bad-002",
    title="Luxury 2BR Penthouse",
    href="/waterloo/luxury-2br-99999",
    price="$3,500/mo",
    beds="2 beds",
    description="Upper floor. In-unit laundry. Cats welcome. Balcony. 2 parking spots.",
)

# Second good listing from a different city
_GOOD_CARD_2 = _listing_card(
    listing_id="good-002",
    title="Spacious 2BR Cambridge",
    href="/cambridge/spacious-2br-11111",
    price="$1,700/mo utilities included",
    beds="2 beds",
    description="Main floor. In-unit washer dryer. Cats confirmed. Patio. 2 parking spots.",
)


def _html_page(*cards: str) -> str:
    return f"<html><body>{''.join(cards)}</body></html>"


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
    )


# ---------------------------------------------------------------------------
# Transport mock — serves different HTML per city URL
# ---------------------------------------------------------------------------

def _make_transport(city_cards: dict[str, str]) -> httpx.MockTransport:
    """Return a MockTransport that responds with city-specific HTML."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for city, html in city_cards.items():
            if city in url:
                return httpx.Response(200, text=html)
        return httpx.Response(200, text="<html><body></body></html>")

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_full_pipeline_with_real_scraper(store, settings):
    """Full pipeline: real scraper parsing HTML → filters → scorer → store → notify.

    Verifies:
    - Real HTML parsing produces RawListing objects
    - Hard filters reject basement/overpriced listings
    - Passing listings get scored and stored
    - Only new passing listings trigger notification
    - RunResult counts are accurate
    """
    transport = _make_transport({
        "kitchener": _html_page(_GOOD_CARD, _BAD_BASEMENT),
        "waterloo": _html_page(_BAD_PRICE),
        "cambridge": _html_page(_GOOD_CARD_2),
    })

    client = httpx.AsyncClient(transport=transport)
    scraper = RentalsCaScraper(client=client)

    notifier = AsyncMock(return_value=True)

    # Patch sleep to avoid real delays from fetch_with_delay
    with patch("rentals_assistant.http.asyncio.sleep", new_callable=AsyncMock):
        result = await run([scraper], store, notifier=notifier, settings=settings)

    # 4 cards total parsed, 2 pass filters, 2 rejected
    assert isinstance(result, RunResult)
    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 0
    assert result.listings_found == 4
    assert result.listings_rejected == 2
    assert result.listings_new == 2
    assert result.listings_notified == 2

    # Notifier called twice (one per passing listing)
    assert notifier.call_count == 2

    # Verify good listings are in store with score/tier
    good_id = make_listing_id("rentals_ca", "good-001")
    cur = store._conn.execute(
        "SELECT score, tier, notified FROM listings WHERE id = ?", (good_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] is not None  # has a score
    assert row[1] is not None  # has a tier
    assert row[2] == 1  # marked notified

    # Verify rejected listings stored with tier=None
    bad_id = make_listing_id("rentals_ca", "bad-001")
    cur = store._conn.execute(
        "SELECT tier, notified FROM listings WHERE id = ?", (bad_id,)
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] is None  # tier is NULL
    assert row[1] == 0


@pytest.mark.asyncio
async def test_e2e_deduplication_on_second_run(store, settings):
    """Second run with same listings should NOT re-notify."""
    transport = _make_transport({
        "kitchener": _html_page(_GOOD_CARD),
        "waterloo": _html_page(),
        "cambridge": _html_page(),
    })

    client = httpx.AsyncClient(transport=transport)
    scraper = RentalsCaScraper(client=client)
    notifier = AsyncMock(return_value=True)

    with patch("rentals_assistant.http.asyncio.sleep", new_callable=AsyncMock):
        # First run — listing is new
        result1 = await run([scraper], store, notifier=notifier, settings=settings)
        assert result1.listings_notified == 1

        # Second run — same listing, should be deduped
        notifier.reset_mock()
        client2 = httpx.AsyncClient(transport=transport)
        scraper2 = RentalsCaScraper(client=client2)
        result2 = await run([scraper2], store, notifier=notifier, settings=settings)

    assert result2.listings_found == 1
    assert result2.listings_new == 0
    assert result2.listings_notified == 0
    assert notifier.call_count == 0


@pytest.mark.asyncio
async def test_e2e_scraper_failure_plus_success(store, settings):
    """One scraper fails, another succeeds — pipeline continues and reports both."""
    # Good scraper with mocked transport
    transport = _make_transport({
        "kitchener": _html_page(_GOOD_CARD),
        "waterloo": _html_page(),
        "cambridge": _html_page(),
    })
    good_client = httpx.AsyncClient(transport=transport)
    good_scraper = RentalsCaScraper(client=good_client)

    # Failing scraper — transport returns 500 to exhaust retries
    fail_transport = httpx.MockTransport(
        lambda req: httpx.Response(500, text="Server Error")
    )
    fail_client = httpx.AsyncClient(transport=fail_transport)
    fail_scraper = RentalsCaScraper(client=fail_client)

    notifier = AsyncMock(return_value=True)

    with patch("rentals_assistant.http.asyncio.sleep", new_callable=AsyncMock):
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
    transport = _make_transport({
        "kitchener": _html_page(),
        "waterloo": _html_page(),
        "cambridge": _html_page(),
    })
    client = httpx.AsyncClient(transport=transport)
    scraper = RentalsCaScraper(client=client)
    notifier = AsyncMock(return_value=True)

    with patch("rentals_assistant.http.asyncio.sleep", new_callable=AsyncMock):
        result = await run([scraper], store, notifier=notifier, settings=settings)

    assert result.scrapers_ok == 1
    assert result.scrapers_failed == 0
    assert result.listings_found == 0
    assert result.listings_new == 0
    assert result.listings_notified == 0
    assert result.listings_rejected == 0
