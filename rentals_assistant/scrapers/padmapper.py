import httpx
from bs4 import BeautifulSoup

from ..models import RawListing
from .base import Scraper
from .parsers import (
    parse_bedrooms,
    parse_floor_level,
    parse_laundry,
    parse_outdoor_space,
    parse_parking,
    parse_pets,
    parse_price,
    parse_utilities,
)

_SEARCH_URL = "https://www.padmapper.com/apartments/waterloo-on?bedrooms=2"
_BASE = "https://www.padmapper.com"


class PadMapperScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; rentals-assistant/1.0)"},
            timeout=30,
        )

    async def fetch(self) -> list[RawListing]:
        response = await self._client.get(_SEARCH_URL)
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[RawListing] = []
        for card in soup.select("ul.listings-list li.listing-card"):
            listing = self._parse_card(card)
            if listing:
                results.append(listing)
        return results

    def _parse_card(self, card) -> RawListing | None:
        link_el = card.select_one("a.listing-card__link")
        if not link_el:
            return None

        title_el = card.select_one("span.listing-card__title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        href = link_el.get("href", "")
        padmapper_url = f"{_BASE}{href}" if href.startswith("/") else href

        # Check for Kijiji duplicate
        source_el = card.select_one("a.listing-card__source")
        if source_el:
            source_href = source_el.get("href", "")
            if "kijiji.ca" in source_href:
                kijiji_id = source_href.rstrip("/").split("/")[-1]
                return RawListing(
                    source="kijiji",
                    external_id=kijiji_id,
                    url=source_href,
                    title=title,
                    price_cad=parse_price(self._price_text(card)),
                    bedrooms=parse_bedrooms(self._beds_text(card)),
                    city=self._city(card),
                    floor_level=parse_floor_level(self._desc(card)),
                    laundry_inunit=parse_laundry(self._desc(card)),
                    outdoor_space=parse_outdoor_space(self._desc(card)),
                    parking_spots=parse_parking(self._desc(card)),
                    pets=parse_pets(self._desc(card)),
                    utilities=parse_utilities(self._price_text(card) + " " + self._desc(card)),
                )

        external_id = str(card.get("data-id") or "")
        return RawListing(
            source="padmapper",
            external_id=external_id,
            url=padmapper_url,
            title=title,
            price_cad=parse_price(self._price_text(card)),
            bedrooms=parse_bedrooms(self._beds_text(card)),
            city=self._city(card),
            floor_level=parse_floor_level(self._desc(card)),
            laundry_inunit=parse_laundry(self._desc(card)),
            outdoor_space=parse_outdoor_space(self._desc(card)),
            parking_spots=parse_parking(self._desc(card)),
            pets=parse_pets(self._desc(card)),
            utilities=parse_utilities(self._price_text(card) + " " + self._desc(card)),
        )

    def _price_text(self, card) -> str:
        el = card.select_one(".listing-card__price")
        return el.get_text(strip=True) if el else ""

    def _beds_text(self, card) -> str:
        el = card.select_one(".listing-card__beds")
        return el.get_text(strip=True) if el else ""

    def _desc(self, card) -> str:
        el = card.select_one(".listing-card__description")
        return el.get_text(strip=True) if el else ""

    def _city(self, card) -> str | None:
        el = card.select_one(".listing-card__location")
        if not el:
            return None
        text = el.get_text(strip=True)
        # "Cambridge, ON" -> "cambridge"
        return text.split(",")[0].strip().lower()
