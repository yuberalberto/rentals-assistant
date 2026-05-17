import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.liv_rent import (
    LivRentScraper,
    _parse_floor_level,
    _parse_laundry,
    _parse_outdoor,
    _parse_parking,
    _parse_pets,
    _parse_utilities,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def load_fixture_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def make_mock_client(gql_response: dict, detail_html: str) -> AsyncMock:
    gql_resp = MagicMock()
    gql_resp.json = MagicMock(return_value=gql_response)
    gql_resp.raise_for_status = MagicMock()

    detail_resp = MagicMock()
    detail_resp.text = detail_html
    detail_resp.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=gql_resp)
    client.get = AsyncMock(return_value=detail_resp)
    return client


# ── _parse_utilities ──────────────────────────────────────────────────────────

def test_parse_utilities_included_when_type_is_included():
    utils = [{"name": "Heat", "type": "included", "txt_id": "heat"}]
    assert _parse_utilities(utils) == "included"


def test_parse_utilities_included_when_multiple_included():
    utils = [
        {"name": "Heat", "type": "included", "txt_id": "heat"},
        {"name": "Water", "type": "included", "txt_id": "water"},
    ]
    assert _parse_utilities(utils) == "included"


def test_parse_utilities_unknown_when_empty():
    assert _parse_utilities([]) is None


def test_parse_utilities_extra_when_no_included_type():
    utils = [{"name": "Heat", "type": "extra", "txt_id": "heat"}]
    assert _parse_utilities(utils) == "extra"


# ── _parse_pets ───────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed_when_allow_cats_is_one():
    assert _parse_pets("1", "1") == "cats_confirmed"


def test_parse_pets_cats_confirmed_even_if_allow_pets_is_zero():
    assert _parse_pets("0", "1") == "cats_confirmed"


def test_parse_pets_allowed_when_allow_pets_one_and_cats_null():
    assert _parse_pets("1", None) == "allowed"


def test_parse_pets_not_allowed_when_allow_pets_zero():
    assert _parse_pets("0", None) == "not_allowed"


def test_parse_pets_unknown_when_both_null():
    assert _parse_pets(None, None) is None


# ── _parse_parking ────────────────────────────────────────────────────────────

def test_parse_parking_zero_when_not_available():
    fees = [{"fee_txt_id": "parking", "fee_frequency_txt_id": "not_available", "fee": None}]
    assert _parse_parking(fees) == 0


def test_parse_parking_one_when_monthly():
    fees = [{"fee_txt_id": "parking", "fee_frequency_txt_id": "monthly", "fee": "75.00"}]
    assert _parse_parking(fees) == 1


def test_parse_parking_one_when_free():
    fees = [{"fee_txt_id": "parking", "fee_frequency_txt_id": "free", "fee": None}]
    assert _parse_parking(fees) == 1


def test_parse_parking_unknown_when_no_parking_fee():
    fees = [{"fee_txt_id": "storage", "fee_frequency_txt_id": "free", "fee": None}]
    assert _parse_parking(fees) is None


def test_parse_parking_unknown_when_empty():
    assert _parse_parking([]) is None


# ── _parse_floor_level ────────────────────────────────────────────────────────

def test_parse_floor_level_upper_when_floor_three():
    assert _parse_floor_level("3") == "upper"


def test_parse_floor_level_upper_when_floor_int():
    assert _parse_floor_level(5) == "upper"


def test_parse_floor_level_main_when_floor_one():
    assert _parse_floor_level("1") == "main"


def test_parse_floor_level_basement_when_floor_zero():
    assert _parse_floor_level("0") == "basement"


def test_parse_floor_level_basement_when_floor_negative():
    assert _parse_floor_level("-1") == "basement"


def test_parse_floor_level_unknown_when_none():
    assert _parse_floor_level(None) is None


def test_parse_floor_level_unknown_when_invalid_string():
    assert _parse_floor_level("ground") is None


# ── _parse_laundry ────────────────────────────────────────────────────────────

def test_parse_laundry_true_when_washer_in_stub_features():
    stub_features = [{"txt_id": "washer", "type": "private"}]
    assert _parse_laundry(stub_features, []) is True


def test_parse_laundry_true_when_dryer_in_unit_features():
    unit_features = [{"txt_id": "dryer", "type": "private"}]
    assert _parse_laundry([], unit_features) is True


def test_parse_laundry_true_when_both_in_mixed_sources():
    stub_features = [{"txt_id": "washer", "type": "private"}]
    unit_features = [{"txt_id": "dryer", "type": "private"}]
    assert _parse_laundry(stub_features, unit_features) is True


def test_parse_laundry_unknown_when_no_laundry_features():
    assert _parse_laundry([], []) is None


def test_parse_laundry_unknown_when_only_other_features():
    features = [{"txt_id": "dishwasher", "type": "private"}]
    assert _parse_laundry(features, []) is None


# ── _parse_outdoor ────────────────────────────────────────────────────────────

def test_parse_outdoor_true_when_balcony_in_stub_features():
    stub_features = [{"txt_id": "balcony", "type": "private"}]
    assert _parse_outdoor(stub_features, [], None) is True


def test_parse_outdoor_true_when_balcony_in_unit_features():
    unit_features = [{"txt_id": "balcony", "type": "private"}]
    assert _parse_outdoor([], unit_features, None) is True


def test_parse_outdoor_true_when_count_balconies_positive():
    assert _parse_outdoor([], [], "1") is True


def test_parse_outdoor_true_when_patio_in_features():
    features = [{"txt_id": "patio", "type": "private"}]
    assert _parse_outdoor(features, [], None) is True


def test_parse_outdoor_unknown_when_no_outdoor_data():
    assert _parse_outdoor([], [], None) is None


def test_parse_outdoor_unknown_when_count_balconies_zero():
    assert _parse_outdoor([], [], "0") is None


# ── _build_listing ────────────────────────────────────────────────────────────

def test_build_listing_sets_source_to_liv_rent():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "The Grand", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.source == "liv_rent"


def test_build_listing_sets_correct_url():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "The Grand", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.url == "https://liv.rent/rental-listings/100001"


def test_build_listing_uses_building_name_as_title():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "The Grand Apartments",
            "full_street_name": "123 Main St", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.title == "The Grand Apartments"


def test_build_listing_falls_back_to_street_name_when_no_building_name():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": None,
            "full_street_name": "123 Main St", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.title == "123 Main St"


def test_build_listing_extracts_price():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.price_cad == 1850


def test_build_listing_extracts_bedrooms():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.bedrooms == 2


def test_build_listing_extracts_city():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.city == "Kitchener"


def test_build_listing_uses_detail_for_pets():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    detail = {"listings": {"allow_pets": "1", "allow_cats": "1", "listing_fees": []}}
    result = scraper._build_listing(stub, detail)
    assert result.pets == "cats_confirmed"


def test_build_listing_uses_detail_for_parking():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    detail = {"listings": {"allow_pets": None, "allow_cats": None,
                           "listing_fees": [{"fee_txt_id": "parking",
                                             "fee_frequency_txt_id": "monthly", "fee": "75.00"}]}}
    result = scraper._build_listing(stub, detail)
    assert result.parking_spots == 1


def test_build_listing_uses_detail_for_floor_level():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    detail = {"unit": {"floor_number": "4", "count_balconies": None, "unit_features": []}}
    result = scraper._build_listing(stub, detail)
    assert result.floor_level == "upper"


def test_build_listing_unknown_pets_when_detail_empty():
    scraper = LivRentScraper(client=MagicMock())
    stub = {"listing_id": 100001, "city": "Kitchener", "bedrooms": 2, "price": 1850,
            "price_frequency": "monthly", "building_name": "X", "utilities": [], "features": []}
    result = scraper._build_listing(stub, {})
    assert result.pets is None


# ── _fetch_city_stubs ─────────────────────────────────────────────────────────

async def test_fetch_city_stubs_returns_monthly_listings_only():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    gql_resp = MagicMock()
    gql_resp.json = MagicMock(return_value=gql_data)
    gql_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=gql_resp)

    scraper = LivRentScraper(client=client)
    result = await scraper._fetch_city_stubs("Kitchener")

    listing_ids = [r["listing_id"] for r in result]
    assert 100001 in listing_ids
    assert 100002 in listing_ids
    assert 100003 not in listing_ids  # daily — filtered out


async def test_fetch_city_stubs_posts_to_gql_endpoint():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    gql_resp = MagicMock()
    gql_resp.json = MagicMock(return_value=gql_data)
    gql_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=gql_resp)

    scraper = LivRentScraper(client=client)
    await scraper._fetch_city_stubs("Kitchener")

    called_url = client.post.call_args.args[0]
    assert "nemesis-prod.liv.rent" in called_url


async def test_fetch_city_stubs_includes_city_in_query():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    gql_resp = MagicMock()
    gql_resp.json = MagicMock(return_value=gql_data)
    gql_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=gql_resp)

    scraper = LivRentScraper(client=client)
    await scraper._fetch_city_stubs("Waterloo")

    payload = client.post.call_args.kwargs.get("json") or client.post.call_args.args[1]
    assert "Waterloo" in payload["query"]


# ── _fetch_detail ─────────────────────────────────────────────────────────────

async def test_fetch_detail_extracts_redux_listing_state():
    detail_html = load_fixture_html("liv_rent_detail.html")
    detail_resp = MagicMock()
    detail_resp.text = detail_html
    detail_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(return_value=detail_resp)

    scraper = LivRentScraper(client=client)
    result = await scraper._fetch_detail(100001)

    assert "listings" in result
    assert result["listings"]["allow_cats"] == "1"


async def test_fetch_detail_fetches_correct_url():
    detail_resp = MagicMock()
    detail_resp.text = "<html></html>"
    detail_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(return_value=detail_resp)

    scraper = LivRentScraper(client=client)
    await scraper._fetch_detail(100001)

    called_url = client.get.call_args.args[0]
    assert "100001" in called_url
    assert "liv.rent/rental-listings" in called_url


async def test_fetch_detail_returns_empty_dict_when_no_next_data():
    detail_resp = MagicMock()
    detail_resp.text = "<html><body>No data here</body></html>"
    detail_resp.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(return_value=detail_resp)

    scraper = LivRentScraper(client=client)
    result = await scraper._fetch_detail(99999)

    assert result == {}


# ── fetch() — end-to-end ──────────────────────────────────────────────────────

async def test_fetch_queries_all_three_cities():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    client = make_mock_client(gql_data, load_fixture_html("liv_rent_detail.html"))

    await LivRentScraper(client=client).fetch()

    post_calls = client.post.call_args_list
    queries = [call.kwargs.get("json", {}).get("query", "") for call in post_calls]
    assert any("Kitchener" in q for q in queries)
    assert any("Waterloo" in q for q in queries)
    assert any("Cambridge" in q for q in queries)


async def test_fetch_returns_raw_listing_instances():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    client = make_mock_client(gql_data, load_fixture_html("liv_rent_detail.html"))

    results = await LivRentScraper(client=client).fetch()

    assert all(isinstance(r, RawListing) for r in results)


async def test_fetch_gracefully_handles_detail_failure():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    gql_resp = MagicMock()
    gql_resp.json = MagicMock(return_value=gql_data)
    gql_resp.raise_for_status = MagicMock()

    client = AsyncMock()
    client.post = AsyncMock(return_value=gql_resp)
    client.get = AsyncMock(side_effect=Exception("connection error"))

    results = await LivRentScraper(client=client).fetch()

    assert isinstance(results, list)
    assert all(isinstance(r, RawListing) for r in results)
    assert all(r.pets is None for r in results)


async def test_fetch_aggregate_count_covers_all_cities():
    gql_data = load_fixture_json("liv_rent_listings_kitchener.json")
    client = make_mock_client(gql_data, load_fixture_html("liv_rent_detail.html"))

    results = await LivRentScraper(client=client).fetch()

    assert len(results) == 6  # 2 monthly listings × 3 cities
