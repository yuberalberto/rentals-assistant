import json
import logging
import re

from ..http import fetch_curl
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

logger = logging.getLogger(__name__)

_CITIES = ["kitchener", "waterloo", "cambridge"]
_BASE_URL = "https://rentals.ca/{city}?beds-min=2&beds-max=2"


class RentalsCaScraper(Scraper):
    def __init__(self, *, _fetch=None) -> None:
        self._fetch_fn = _fetch or fetch_curl

    async def fetch(self) -> list[RawListing]:
        listings: list[RawListing] = []
        for city in _CITIES:
            url = _BASE_URL.format(city=city)
            try:
                html = await self._fetch_fn(url)
                listings.extend(self._parse(html, city))
            except Exception as exc:
                logger.warning("Rentals.ca %s failed: %s", city, exc)
        return listings

    def _parse(self, html: str, city: str) -> list[RawListing]:
        edges = _extract_edges(html)
        results: list[RawListing] = []
        for edge in edges:
            try:
                listing = self._parse_node(edge.get("node", {}), city)
                if listing:
                    results.append(listing)
            except Exception as exc:
                logger.debug("Skipping malformed Rentals.ca node: %s", exc)
        return results

    def _parse_node(self, node: dict, fallback_city: str) -> RawListing | None:
        path = node.get("path", "")
        name = node.get("rentalListingName", "")
        if not path:
            return None

        url = f"https://rentals.ca/{path}"
        external_id = node.get("id", path)

        rent_range = node.get("rentRange") or []
        price = int(rent_range[0]) if rent_range else None

        beds_range = node.get("bedsRange") or []
        bedrooms = int(beds_range[-1]) if beds_range else None

        baths_range = node.get("bathsRange") or []
        bathrooms = float(baths_range[0]) if baths_range else None

        address = node.get("address") or {}
        city_info = address.get("city") or {}
        city = (city_info.get("citySlug") or fallback_city).lower()

        street = address.get("street", "")
        title = f"{name} — {street}" if street else name

        return RawListing(
            source="rentals_ca",
            external_id=external_id,
            url=url,
            title=title,
            price_cad=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            city=city,
            floor_level=parse_floor_level(title),
            laundry_inunit=parse_laundry(title),
            outdoor_space=parse_outdoor_space(title),
            parking_spots=parse_parking(title),
            pets=parse_pets(title),
            utilities=parse_utilities(title),
        )


def _extract_edges(html: str) -> list[dict]:
    """Extract listing edges from embedded JSON in page script."""
    match = re.search(r'response:\s*(\{"data".*)', html)
    if not match:
        logger.warning("Rentals.ca: could not find embedded JSON data")
        return []

    json_str = match.group(1)

    # Find balanced braces to isolate the JSON object
    depth = 0
    end = 0
    for i, ch in enumerate(json_str):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0:
            end = i + 1
            break

    try:
        data = json.loads(json_str[:end])
    except json.JSONDecodeError as exc:
        logger.warning("Rentals.ca: failed to parse embedded JSON: %s", exc)
        return []

    return data.get("data", {}).get("edges", [])
