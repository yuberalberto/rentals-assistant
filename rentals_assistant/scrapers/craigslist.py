import logging
import re

from bs4 import BeautifulSoup

from rentals_assistant.http import fetch_curl
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

_SEARCH_URL = "https://hamilton.craigslist.org/search/apa?query=2+bedroom"


class CraigslistScraper(Scraper):
    """Craigslist HTML scraper for Hamilton area apartments."""

    def __init__(self, *, _fetch=None) -> None:
        self._fetch_fn = _fetch or fetch_curl

    async def fetch(self) -> list[RawListing]:
        html = await self._fetch_fn(_SEARCH_URL)
        return self._parse(html)

    def _parse(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        city_map = _extract_city_map(soup)
        listings: list[RawListing] = []

        for idx, item in enumerate(soup.select("li.cl-static-search-result")):
            try:
                listing = self._parse_item(item, city_map.get(idx))
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.debug("Skipping malformed Craigslist item: %s", exc)

        if not listings:
            logger.warning("Craigslist returned 0 listings — site structure may have changed")

        return listings

    def _parse_item(self, item, city: str | None) -> RawListing | None:
        link_el = item.select_one("a")
        if not link_el:
            return None

        url = link_el.get("href", "")
        if not url:
            return None

        title_el = item.select_one(".title")
        title = title_el.get_text(strip=True) if title_el else item.get("title", "")

        price_el = item.select_one(".price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        external_id = url.rstrip("/").split("/")[-1].replace(".html", "")

        return RawListing(
            source="craigslist",
            external_id=external_id,
            url=url,
            title=title,
            price_cad=_parse_price(price_text),
            bedrooms=2,
            city=city,
            floor_level=parse_floor_level(title),
            laundry_inunit=parse_laundry(title),
            outdoor_space=parse_outdoor_space(title),
            parking_spots=parse_parking(title),
            pets=parse_pets(title),
            utilities=parse_utilities(title),
        )


def _parse_price(text: str) -> int | None:
    m = re.search(r"\$\s*([\d,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None


def _extract_city_map(soup: BeautifulSoup) -> dict[int, str]:
    """Build index→city map from the JSON-LD search results script."""
    import json

    script = soup.find("script", id="ld_searchpage_results")
    if not script or not script.string:
        return {}
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return {}

    city_map: dict[int, str] = {}
    for entry in data.get("itemListElement", []):
        try:
            idx = int(entry["position"])
            locality = entry["item"]["address"]["addressLocality"]
            city_map[idx] = locality.strip().lower()
        except (KeyError, ValueError, TypeError):
            continue
    return city_map
