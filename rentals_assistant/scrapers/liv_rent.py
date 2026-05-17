import asyncio
import json
import re

import httpx

from ..http import create_client
from ..models import RawListing
from .base import Scraper

_GQL_URL = "https://nemesis-prod.liv.rent/graphql"
_DETAIL_BASE = "https://liv.rent/rental-listings"
_CITIES = ["Kitchener", "Waterloo", "Cambridge"]
_PAGE_SIZE = 100

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)

_GQL_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://liv.rent",
    "Referer": "https://liv.rent/",
}

_LIST_QUERY_TPL = """\
query {{
  listSearch {{
    listings(input: {{
      bedroom_count: ["2"],
      cities: {cities_json},
      page: {page},
      page_size: {page_size},
      housing_types: [],
      unit_subtypes: [],
      unit_types: [],
      useCollapse: false,
      featured: 0
    }}) {{
      metadata {{ total_count page page_size }}
      feed {{
        listing_id
        city
        state
        bedrooms
        price
        price_frequency
        full_street_name
        building_name
        building_type
        utilities {{ name type txt_id }}
        features {{ name type txt_id }}
      }}
    }}
  }}
}}"""


class LivRentScraper(Scraper):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or create_client(timeout=30)

    async def fetch(self) -> list[RawListing]:
        stubs: list[dict] = []
        for city in _CITIES:
            stubs.extend(await self._fetch_city_stubs(city))

        details = await asyncio.gather(
            *(self._fetch_detail(s["listing_id"]) for s in stubs),
            return_exceptions=True,
        )

        return [
            self._build_listing(stub, det if not isinstance(det, Exception) else {})
            for stub, det in zip(stubs, details, strict=True)
        ]

    async def _fetch_city_stubs(self, city: str) -> list[dict]:
        query = _LIST_QUERY_TPL.format(
            cities_json=json.dumps([city]),
            page=1,
            page_size=_PAGE_SIZE,
        )
        resp = await self._client.post(
            _GQL_URL,
            json={"query": query},
            headers=_GQL_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
        feed = (
            data.get("data", {})
            .get("listSearch", {})
            .get("listings", {})
            .get("feed", [])
        )
        return [item for item in feed if item.get("price_frequency") == "monthly"]

    async def _fetch_detail(self, listing_id: int) -> dict:
        resp = await self._client.get(f"{_DETAIL_BASE}/{listing_id}")
        resp.raise_for_status()
        m = _NEXT_DATA_RE.search(resp.text)
        if not m:
            return {}
        data = json.loads(m.group(1))
        return (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialReduxState", {})
            .get("listing", {})
        )

    def _build_listing(self, stub: dict, detail: dict) -> RawListing:
        listing_data = detail.get("listings") or {}
        unit_data = detail.get("unit") or {}
        stub_features = stub.get("features") or []
        unit_features = unit_data.get("unit_features") or []

        return RawListing(
            source="liv_rent",
            external_id=str(stub["listing_id"]),
            url=f"{_DETAIL_BASE}/{stub['listing_id']}",
            title=stub.get("building_name") or stub.get("full_street_name", ""),
            price_cad=int(stub["price"]) if stub.get("price") is not None else None,
            bedrooms=stub.get("bedrooms"),
            city=stub.get("city"),
            floor_level=_parse_floor_level(unit_data.get("floor_number")),
            laundry_inunit=_parse_laundry(stub_features, unit_features),
            outdoor_space=_parse_outdoor(stub_features, unit_features, unit_data.get("count_balconies")),
            parking_spots=_parse_parking(listing_data.get("listing_fees") or []),
            pets=_parse_pets(listing_data.get("allow_pets"), listing_data.get("allow_cats")),
            utilities=_parse_utilities(stub.get("utilities") or []),
        )


def _parse_utilities(utilities: list[dict]) -> str | None:
    if not utilities:
        return None
    if any(u.get("type") == "included" for u in utilities):
        return "included"
    return "extra"


def _parse_pets(allow_pets: str | None, allow_cats: str | None) -> str | None:
    if allow_cats == "1":
        return "cats_confirmed"
    if allow_pets == "1":
        return "allowed"
    if allow_pets == "0":
        return "not_allowed"
    return None


def _parse_parking(listing_fees: list[dict]) -> int | None:
    for fee in listing_fees:
        if fee.get("fee_txt_id") == "parking":
            freq = fee.get("fee_frequency_txt_id")
            if freq == "not_available":
                return 0
            if freq in ("free", "monthly", "weekly", "yearly", "annual"):
                return 1
    return None


def _parse_floor_level(floor_number) -> str | None:
    if floor_number is None:
        return None
    try:
        n = int(floor_number)
    except (ValueError, TypeError):
        return None
    if n <= 0:
        return "basement"
    if n == 1:
        return "main"
    return "upper"


def _parse_laundry(stub_features: list[dict], unit_features: list[dict]) -> bool | None:
    all_features = stub_features + unit_features
    txt_ids = {f.get("txt_id") for f in all_features}
    if "washer" in txt_ids or "dryer" in txt_ids:
        return True
    return None


def _parse_outdoor(
    stub_features: list[dict],
    unit_features: list[dict],
    count_balconies,
) -> bool | None:
    all_features = stub_features + unit_features
    txt_ids = {f.get("txt_id") for f in all_features}
    outdoor_ids = {"balcony", "patio", "deck", "terrace", "yard", "patio_deck_terrace"}
    if txt_ids & outdoor_ids:
        return True
    if count_balconies is not None:
        try:
            if int(count_balconies) > 0:
                return True
        except (ValueError, TypeError):
            pass
    return None
