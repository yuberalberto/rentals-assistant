import httpx

from ..http import create_client
from ..models import RawListing
from .base import Scraper
from .parsers import (
    parse_floor_level,
    parse_laundry,
    parse_outdoor_space,
    parse_parking,
    parse_pets,
    parse_utilities,
)

_CITIES = ["kitchener", "waterloo", "cambridge"]
_BASE_URL = "https://www.zumper.com/api/t/{city}/apartments/2-beds"
_BASE = "https://www.zumper.com"


class ZumperScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or create_client(timeout=30)

    async def fetch(self) -> list[RawListing]:
        listings: list[RawListing] = []
        for city in _CITIES:
            response = await self._client.get(_BASE_URL.format(city=city))
            response.raise_for_status()
            listings.extend(self._parse(response.json()))
        return listings

    def _parse(self, data: dict) -> list[RawListing]:
        results: list[RawListing] = []
        for item in data.get("results", []):
            url = item.get("url", "")
            if not url:
                continue

            absolute_url = f"{_BASE}{url}" if url.startswith("/") else url
            desc = item.get("description", "")
            price = item.get("price")
            price_cad = int(price) if isinstance(price, (int, float)) else None

            results.append(
                RawListing(
                    source="zumper",
                    external_id=str(item.get("id", "")),
                    url=absolute_url,
                    title=item.get("title", ""),
                    price_cad=price_cad,
                    bedrooms=item.get("bedrooms"),
                    city=item.get("city", "").lower() if item.get("city") else None,
                    floor_level=parse_floor_level(desc),
                    laundry_inunit=parse_laundry(desc),
                    outdoor_space=parse_outdoor_space(desc),
                    parking_spots=parse_parking(desc),
                    pets=parse_pets(desc),
                    utilities=parse_utilities(desc),
                )
            )
        return results
