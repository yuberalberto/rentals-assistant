import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.zumper import ZumperScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def load_json_fixture(name: str) -> dict:
    return json.loads(load_fixture(name))


# ── return type ───────────────────────────────────────────────────────────────

def test_parse_returns_list():
    data = load_json_fixture("zumper_kw.json")
    assert isinstance(ZumperScraper(client=MagicMock())._parse(data), list)


def test_parse_returns_raw_listing_instances():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert all(isinstance(r, RawListing) for r in result)


def test_parse_returns_three_listings():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert len(result) == 3


# ── required identity fields ──────────────────────────────────────────────────

def test_parse_source_is_zumper():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].source == "zumper"


def test_parse_extracts_external_id():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].external_id == "zumper-101"


def test_parse_extracts_title():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].title == "Modern 2BR - Utilities Included"


def test_parse_extracts_url():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].url == "https://www.zumper.com/p/for-rent/2-bedroom-apartment-kitchener-on/101"


def test_parse_extracts_city_kitchener():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].city == "kitchener"


def test_parse_extracts_city_cambridge():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].city == "cambridge"


def test_parse_extracts_city_waterloo():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].city == "waterloo"


# ── price ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].price_cad == 1800


def test_parse_extracts_price_second_listing():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].price_cad == 1650


# ── bedrooms ──────────────────────────────────────────────────────────────────

def test_parse_extracts_bedrooms():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].bedrooms == 2


# ── utilities ─────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].utilities == "included"


def test_parse_utilities_unknown():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].utilities is None


def test_parse_utilities_extra():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].utilities == "extra"


# ── floor level ───────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].floor_level == "upper"


def test_parse_floor_level_unknown():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].floor_level is None


def test_parse_floor_level_main():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].floor_level == "main"


# ── pets ──────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_not_allowed():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].pets == "not_allowed"


def test_parse_pets_allowed():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].pets == "allowed"


# ── laundry ───────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit_from_insuite():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].laundry_inunit is True


def test_parse_laundry_unknown():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].laundry_inunit is None


def test_parse_laundry_inunit_from_inunit_keyword():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].laundry_inunit is True


# ── outdoor space ─────────────────────────────────────────────────────────────

def test_parse_outdoor_space_balcony():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].outdoor_space is True


def test_parse_outdoor_space_unknown():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].outdoor_space is None


def test_parse_outdoor_space_yard():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].outdoor_space is True


# ── parking ───────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[0].parking_spots == 2


def test_parse_parking_unknown():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[1].parking_spots is None


def test_parse_parking_one_spot():
    data = load_json_fixture("zumper_kw.json")
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result[2].parking_spots == 1


# ── edge cases ────────────────────────────────────────────────────────────────

def test_parse_missing_results_key_returns_empty_list():
    result = ZumperScraper(client=MagicMock())._parse({})
    assert result == []


def test_parse_empty_results_list_returns_empty_list():
    result = ZumperScraper(client=MagicMock())._parse({"results": []})
    assert result == []


def test_parse_skips_item_without_url():
    data = {"results": [{"id": "z-999", "title": "No URL listing", "price": 1500, "bedrooms": 2, "city": "Kitchener", "description": ""}]}
    result = ZumperScraper(client=MagicMock())._parse(data)
    assert result == []


# ── fetch() ───────────────────────────────────────────────────────────────────

async def test_fetch_queries_kitchener_waterloo_cambridge():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=load_json_fixture("zumper_kw.json"))
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    await ZumperScraper(client=mock_client).fetch()

    called_urls = [call.args[0] for call in mock_client.get.call_args_list]
    assert any("kitchener" in u for u in called_urls)
    assert any("waterloo" in u for u in called_urls)
    assert any("cambridge" in u for u in called_urls)


async def test_fetch_aggregates_results_from_all_cities():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=load_json_fixture("zumper_kw.json"))
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await ZumperScraper(client=mock_client).fetch()

    assert len(result) == 9  # 3 listings × 3 cities
