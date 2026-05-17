import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.kw_property import KwPropertyScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# -- return type --

def test_parse_returns_list():
    raw = json.loads(load_fixture("kw_property_api.json"))
    assert isinstance(KwPropertyScraper(client=MagicMock())._parse(raw), list)


def test_parse_returns_raw_listing_instances():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert all(isinstance(r, RawListing) for r in result)


def test_parse_returns_two_listings():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert len(result) == 2


# -- source / identity --

def test_parse_source_is_kw_property():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].source == "kw_property"


def test_parse_extracts_external_id():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].external_id == "69de62142cc52e369d68a493"


def test_parse_extracts_url():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].url == "https://kwproperty.rhenti.com/#/listings/69de62142cc52e369d68a493"


def test_parse_extracts_title_from_address():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert "250 Heslop Rd" in result[0].title


# -- price / bedrooms / city --

def test_parse_extracts_price_cad():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].price_cad == 2650


def test_parse_extracts_bedrooms():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].bedrooms == 3


def test_parse_extracts_city():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].city == "cambridge"
    assert result[1].city == "waterloo"


# -- amenities: pets --

def test_parse_pets_allowed_when_included():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].pets == "allowed"


# -- amenities: laundry --

def test_parse_laundry_inunit_when_ensuite_washer():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].laundry_inunit is True


# -- amenities: parking --

def test_parse_parking_from_amount():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result[0].parking_spots == 2


def test_parse_parking_defaults_to_one_when_present_no_amount():
    raw = json.loads(load_fixture("kw_property_api.json"))
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    # second listing has no parking amenity -> None
    assert result[1].parking_spots is None


# -- edge cases --

def test_parse_empty_list_returns_empty():
    result = KwPropertyScraper(client=MagicMock())._parse([])
    assert result == []


def test_parse_logs_warning_when_zero_listings(caplog):
    caplog.set_level(logging.WARNING)
    KwPropertyScraper(client=MagicMock())._parse([])
    assert "0 listings" in caplog.text


def test_parse_skips_inactive():
    raw = [
        {"_id": "1", "status": "inactive", "price": 1000, "bedrooms": 2, "full_address": "123 Main St", "address_details": {"city": "Kitchener"}, "amenities_list": []}
    ]
    result = KwPropertyScraper(client=MagicMock())._parse(raw)
    assert result == []


# -- fetch --

async def test_fetch_returns_raw_listings():
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=json.loads(load_fixture("kw_property_api.json")))
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await KwPropertyScraper(client=mock_client).fetch()
    assert len(result) == 2
