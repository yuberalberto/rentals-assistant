import httpx
from bs4 import BeautifulSoup

from ..http import create_client, fetch_with_delay
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

_CITIES = ["kitchener", "waterloo", "cambridge"]
_BASE_URL = "https://rentals.ca/{city}?beds-min=2&beds-max=2"


class RentalsCaScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or create_client(timeout=30)

    async def fetch(self) -> list[RawListing]:
        listings: list[RawListing] = []
        for city in _CITIES:
            response = await fetch_with_delay(
                self._client,
                _BASE_URL.format(city=city),
                min_delay=1.0,
                max_delay=3.0,
            )
            response.raise_for_status()
            listings.extend(self._parse(response.text, city))
        return listings

    def _parse(self, html: str, city: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[RawListing] = []
        for card in soup.select("article.listing-card"):
            listing = self._parse_card(card, city)
            if listing:
                results.append(listing)
        return results

    def _parse_card(self, card, city: str) -> RawListing | None:
        title_el = card.select_one("a.listing-card__title")
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        url = f"https://rentals.ca{href}"
        external_id = str(card.get("data-listing-id") or href.split("/")[-1])

        price_el = card.select_one(".listing-card__price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        beds_el = card.select_one(".listing-card__beds")
        beds_text = beds_el.get_text(strip=True) if beds_el else ""

        desc_el = card.select_one(".listing-card__description")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        return RawListing(
            source="rentals_ca",
            external_id=external_id,
            url=url,
            title=title,
            price_cad=parse_price(price_text),
            bedrooms=parse_bedrooms(beds_text),
            city=city,
            floor_level=parse_floor_level(desc),
            laundry_inunit=parse_laundry(desc),
            outdoor_space=parse_outdoor_space(desc),
            parking_spots=parse_parking(desc),
            pets=parse_pets(desc),
            utilities=parse_utilities(price_text + " " + desc),
        )
