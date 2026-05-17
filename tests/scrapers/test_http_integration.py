"""Integration tests: scrapers + resilient HTTP client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from rentals_assistant.http import create_client
from rentals_assistant.scrapers.activa import ActivaScraper
from rentals_assistant.scrapers.craigslist import CraigslistScraper
from rentals_assistant.scrapers.kw_property import KwPropertyScraper
from rentals_assistant.scrapers.liv_rent import LivRentScraper
from rentals_assistant.scrapers.padmapper import PadMapperScraper
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper
from rentals_assistant.scrapers.viewit import ViewItScraper
from rentals_assistant.scrapers.zumper import ZumperScraper

# ── default path uses create_client ──────────────────────────────────────────

@pytest.mark.parametrize(
    "scraper_cls, create_client_path",
    [
        (ActivaScraper, "rentals_assistant.scrapers.activa.create_client"),
        (CraigslistScraper, "rentals_assistant.scrapers.craigslist.create_client"),
        (KwPropertyScraper, "rentals_assistant.scrapers.kw_property.create_client"),
        (LivRentScraper, "rentals_assistant.scrapers.liv_rent.create_client"),
        (PadMapperScraper, "rentals_assistant.scrapers.padmapper.create_client"),
        (RentalsCaScraper, "rentals_assistant.scrapers.rentals_ca.create_client"),
        (ViewItScraper, "rentals_assistant.scrapers.viewit.create_client"),
        (ZumperScraper, "rentals_assistant.scrapers.zumper.create_client"),
    ],
)
def test_default_path_uses_create_client(scraper_cls, create_client_path):
    with patch(create_client_path) as mock_create:
        mock_client = AsyncMock()
        mock_create.return_value = mock_client
        scraper = scraper_cls()
        mock_create.assert_called_once()
        assert scraper._client is mock_client


# ── retry on 503 with mock transport ─────────────────────────────────────────

class _RetryTransport(httpx.MockTransport):
    def __init__(self):
        self.call_count = 0
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        if self.call_count == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, text="<html><body></body></html>", request=request)


@pytest.mark.asyncio
async def test_scraper_retries_503_then_succeeds():
    transport = _RetryTransport()
    client = create_client(transport=transport)
    scraper = ActivaScraper(client=client)
    result = await scraper.fetch()
    assert transport.call_count == 2
    assert result == []


@pytest.mark.asyncio
async def test_rentals_ca_fetch_with_delay_retries_503():
    """RentalsCa uses fetch_with_delay between city requests; verify retry works."""
    transport = _RetryTransport()
    client = create_client(transport=transport)
    scraper = RentalsCaScraper(client=client)
    with patch("rentals_assistant.http.asyncio.sleep"):
        result = await scraper.fetch()
    # 3 cities: first city gets 503 -> retry -> 200 (2 calls), others get 200 (1 each)
    assert transport.call_count == 4
    assert result == []
