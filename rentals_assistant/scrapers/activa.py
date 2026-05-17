import logging

import httpx
from bs4 import BeautifulSoup

from ..http import create_client
from ..models import RawListing
from .base import Scraper
from .parsers import parse_floor_level, parse_price

logger = logging.getLogger(__name__)

# Confirmed base URL for Activa rentals page (Kitchener/Waterloo region)
# https://activa.ca/whats-available/?post_types=rental
_SEARCH_URL = "https://activa.ca/whats-available/?post_types=rental"


class ActivaScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or create_client(timeout=30)

    async def fetch(self) -> list[RawListing]:
        response = await self._client.get(_SEARCH_URL)
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[RawListing] = []
        for card in soup.select("a.home-card"):
            listing = self._parse_card(card)
            if listing:
                results.append(listing)

        if not results:
            logger.warning(
                "Activa scraper returned 0 listings — site structure may have changed"
            )
        return results

    def _parse_card(self, card) -> RawListing | None:
        title_el = card.select_one(".title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = card.get("href", "")
        if not href:
            return None

        external_id = href.rstrip("/").split("/")[-1]

        price_el = card.select_one(".price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        beds_el = card.select_one(".bedrooms")
        beds_text = beds_el.get_text(strip=True) if beds_el else ""
        bedrooms = int(beds_text) if beds_text.isdigit() else None

        parking_el = card.select_one(".parking")
        parking_text = parking_el.get_text(strip=True) if parking_el else ""
        parking_spots = int(parking_text) if parking_text.isdigit() else None

        # City is not present in card HTML; all observed rentals are in Kitchener
        city = "kitchener"

        return RawListing(
            source="activa",
            external_id=external_id,
            url=href,
            title=title,
            price_cad=parse_price(price_text),
            bedrooms=bedrooms,
            city=city,
            floor_level=parse_floor_level(title),
            laundry_inunit=None,  # not available in card; fetch detail page for this
            outdoor_space=None,
            parking_spots=parking_spots,
            pets=None,
            utilities=None,
        )
