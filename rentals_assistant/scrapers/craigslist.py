import logging
import re
import xml.etree.ElementTree as ET

import httpx

from rentals_assistant.http import create_client
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

_RSS_URL = "https://hamilton.craigslist.org/search/apa?format=rss&query=2+bedroom"

_CRAIGSLIST_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# RSS 1.0 / RDF namespaces used by Craigslist
_NS_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_NS_RSS = "http://purl.org/rss/1.0/"
_NS_DC = "http://purl.org/dc/elements/1.1/"


class CraigslistScraper(Scraper):
    """Craigslist RSS feed parser for Hamilton area apartments.

    Consumes the RSS feed and returns normalised ``RawListing`` objects.
    Handles malformed or missing fields gracefully per-item so that a
    single bad entry never aborts the entire scrape.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or create_client(headers=_CRAIGSLIST_UA, timeout=30)

    async def fetch(self) -> list[RawListing]:
        response = await self._client.get(_RSS_URL)
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, xml_text: str) -> list[RawListing]:
        listings: list[RawListing] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Failed to parse Craigslist RSS: %s", exc)
            return listings

        # RSS 1.0 items are <item> elements inside <rdf:RDF>
        for item in root.iter(f"{{{_NS_RSS}}}item"):
            try:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.debug("Skipping malformed Craigslist RSS item: %s", exc)

        if not listings:
            logger.warning("Craigslist RSS returned 0 listings — feed structure may have changed")

        return listings

    def _parse_item(self, item: ET.Element) -> RawListing | None:
        """Parse a single <item> element into a ``RawListing``."""
        title = _text(item, f"{{{_NS_RSS}}}title") or ""
        link = _text(item, f"{{{_NS_RSS}}}link") or ""
        description = _text(item, f"{{{_NS_RSS}}}description") or ""

        if not link:
            return None

        # Use URL as external_id (unique per listing)
        external_id = link.rstrip("/").split("/")[-1].replace(".html", "")

        full_text = f"{title} {description}"

        return RawListing(
            source="craigslist",
            external_id=external_id,
            url=link,
            title=title,
            price_cad=_parse_craigslist_price(title),
            bedrooms=2,
            city=_parse_city(title),
            floor_level=parse_floor_level(full_text),
            laundry_inunit=parse_laundry(full_text),
            outdoor_space=parse_outdoor_space(full_text),
            parking_spots=parse_parking(full_text),
            pets=parse_pets(full_text),
            utilities=parse_utilities(full_text),
        )


def _text(parent: ET.Element, tag: str) -> str | None:
    """Safely get stripped text from the first child matching *tag*."""
    el = parent.find(tag)
    return (el.text or "").strip() if el is not None else None


def _parse_craigslist_price(title: str) -> int | None:
    """Extract monthly price from Craigslist title like '$1,850 / 2br - ...'."""
    m = re.search(r"\$\s*([\d,]+)", title)
    return int(m.group(1).replace(",", "")) if m else None


def _parse_city(title: str) -> str | None:
    """Extract city from title like '... (Kitchener)'."""
    m = re.search(r"\(([A-Za-z\s]+)\)\s*$", title)
    return m.group(1).strip().lower() if m else None
