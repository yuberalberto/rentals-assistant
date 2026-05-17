import logging

import httpx

from ..models import RawListing
from .base import Scraper

logger = logging.getLogger(__name__)

# KW Property uses rhenti.com white-label platform.
# Confirmed base URL for listings API:
# https://api.rhenti.com/properties?whitelabel=6931f6f3cd23c75167f8dd66
_API_URL = (
    "https://api.rhenti.com/properties"
    "?bottomLeftCorner=-80.5&bottomLeftCorner=43.2"
    "&topRightCorner=-79.5&topRightCorner=43.7"
    "&whitelabel=6931f6f3cd23c75167f8dd66"
)
_WHITELABEL_BASE = "https://kwproperty.rhenti.com"

# Cities we care about in KW region
_KW_CITIES = {"kitchener", "waterloo", "cambridge"}


class KwPropertyScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; rentals-assistant/1.0)"},
            timeout=30,
        )

    async def fetch(self) -> list[RawListing]:
        response = await self._client.get(_API_URL)
        response.raise_for_status()
        data = response.json()
        return self._parse(data)

    def _parse(self, data: list[dict]) -> list[RawListing]:
        results: list[RawListing] = []
        for item in data:
            if item.get("status") != "active":
                continue
            city = (item.get("address_details", {}).get("city") or "").lower()
            if city not in _KW_CITIES:
                continue
            listing = self._parse_item(item, city)
            if listing:
                results.append(listing)

        if not results:
            logger.warning(
                "KW Property scraper returned 0 listings — site/API may have changed"
            )
        return results

    def _parse_item(self, item: dict, city: str) -> RawListing:
        external_id = str(item.get("_id", ""))
        url = f"{_WHITELABEL_BASE}/#/listings/{external_id}"
        title = item.get("full_address", "KW Property Listing")
        price = item.get("price")
        bedrooms = item.get("bedrooms")

        amenities = item.get("amenities_list", [])

        pets = self._parse_pets(amenities)
        laundry = self._parse_laundry(amenities)
        parking = self._parse_parking(amenities)

        return RawListing(
            source="kw_property",
            external_id=external_id,
            url=url,
            title=title,
            price_cad=int(price) if isinstance(price, (int, float)) else None,
            bedrooms=int(bedrooms) if isinstance(bedrooms, (int, float)) else None,
            city=city,
            floor_level=None,
            laundry_inunit=laundry,
            outdoor_space=None,
            parking_spots=parking,
            pets=pets,
            utilities=None,
        )

    def _parse_pets(self, amenities: list[dict]) -> str | None:
        for a in amenities:
            if a.get("name") == "pets" and a.get("included_in_apartment") is True:
                return "allowed"
        return None

    def _parse_laundry(self, amenities: list[dict]) -> bool | None:
        names = {a.get("name") for a in amenities}
        if "ensuite_washer" in names or "ensuite_dryer" in names:
            return True
        if "laundry_facilities" in names:
            return False
        return None

    def _parse_parking(self, amenities: list[dict]) -> int | None:
        for a in amenities:
            if a.get("name") in ("parking", "outdoor_parking"):
                amount = a.get("amount")
                if isinstance(amount, (int, float)) and amount > 0:
                    return int(amount)
        for a in amenities:
            if a.get("name") in ("parking", "outdoor_parking") and (
                a.get("included_in_apartment") is True or a.get("included_in_building") is True
            ):
                return 1
        return None
