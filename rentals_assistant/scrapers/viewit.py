import logging
import re

from bs4 import BeautifulSoup

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.base import Scraper
from rentals_assistant.scrapers.parsers import (
    parse_floor_level,
    parse_laundry,
    parse_outdoor_space,
    parse_parking,
    parse_pets,
    parse_utilities,
)

logger = logging.getLogger(__name__)

_CITIES = ["Kitchener", "Cambridge", "Waterloo"]
_BASE = "https://www.viewit.ca/Listings?City={city}&Rooms=2"


class ViewItScraper(Scraper):
    """ViewIt.ca scraper — uses httpx + BeautifulSoup.

    ViewIt.ca renders listings server-side when accessed with the correct
    search URL.  Each city is scraped individually.
    """

    def __init__(self, client=None) -> None:
        import httpx

        self._client = client or httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=30,
            follow_redirects=True,
        )

    async def fetch(self) -> list[RawListing]:
        listings: list[RawListing] = []
        for city in _CITIES:
            url = _BASE.format(city=city)
            try:
                response = await self._client.get(url)
                response.raise_for_status()
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", url, exc)
                continue

            page_listings = self._parse(response.text, city)
            if not page_listings:
                logger.warning("ViewIt.ca %s returned 0 listings — site structure may have changed", city)
            listings.extend(page_listings)

        return listings

    def _parse(self, html: str, city: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[RawListing] = []

        # ViewIt.ca renders listings inside <section class="featuredListing">
        for card in soup.select("section.featuredListing"):
            listing = self._parse_card(card, city)
            if listing:
                results.append(listing)

        return results

    def _parse_card(self, card, city: str) -> RawListing | None:
        link_el = card.select_one("a[href*='href.aspx']")
        if not link_el:
            return None

        href = link_el.get("href", "")
        url = href if href.startswith("http") else f"https:{href}"

        # Extract external_id from cid parameter
        m = re.search(r"cid=(\d+)", href)
        external_id = m.group(1) if m else href

        title_el = card.select_one(".featuredListing-name")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price_el = card.select_one(".featuredListing-price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        desc_el = card.select_one(".featuredListing-description")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        full_text = f"{title} {desc}"

        return RawListing(
            source="viewit",
            external_id=external_id,
            url=url,
            title=title,
            price_cad=_parse_viewit_price(price_text),
            bedrooms=2,
            city=city,
            floor_level=parse_floor_level(full_text),
            laundry_inunit=parse_laundry(full_text),
            outdoor_space=parse_outdoor_space(full_text),
            parking_spots=parse_parking(full_text),
            pets=parse_pets(full_text),
            utilities=parse_utilities(price_text + " " + desc),
        )


def _parse_viewit_price(text: str) -> int | None:
    """Extract monthly price from ViewIt.ca price text."""
    m = re.search(r"\$\s*([\d,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None
