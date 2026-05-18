from pathlib import Path
from unittest.mock import AsyncMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.craigslist import (
    CraigslistScraper,
    _extract_city_map,
    _parse_price,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── _parse_price ─────────────────────────────────────────────────────────────

def test_parse_price_extracts_number():
    assert _parse_price("$1,850") == 1850


def test_parse_price_returns_none_when_missing():
    assert _parse_price("Price TBD") is None


def test_parse_price_returns_none_for_empty():
    assert _parse_price("") is None


# ── _extract_city_map ────────────────────────────────────────────────────────

def test_extract_city_map_from_fixture():
    from bs4 import BeautifulSoup
    html = load_fixture("craigslist_hamilton.html")
    soup = BeautifulSoup(html, "html.parser")
    city_map = _extract_city_map(soup)
    assert city_map[0] == "kitchener"
    assert city_map[1] == "cambridge"


# ── return type ──────────────────────────────────────────────────────────────

def test_parse_returns_list():
    html = load_fixture("craigslist_hamilton.html")
    scraper = CraigslistScraper()
    assert isinstance(scraper._parse(html), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("craigslist_hamilton.html")
    scraper = CraigslistScraper()
    assert all(isinstance(r, RawListing) for r in scraper._parse(html))


def test_parse_returns_four_listings():
    html = load_fixture("craigslist_hamilton.html")
    scraper = CraigslistScraper()
    assert len(scraper._parse(html)) == 4


# ── required identity fields ────────────────────────────────────────────────

def test_parse_source_is_craigslist():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].source == "craigslist"


def test_parse_extracts_title():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert "Bright Upper Floor 2BR" in result[0].title


def test_parse_extracts_url():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].url == "https://hamilton.craigslist.org/apa/1.html"


def test_parse_extracts_external_id():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].external_id == "1"


# ── price ────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].price_cad == 1850


def test_parse_price_second_item():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].price_cad == 1650


def test_parse_handles_missing_price_gracefully():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[3].price_cad is None


# ── city ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_city():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].city == "kitchener"


def test_parse_city_second_item():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].city == "cambridge"


# ── pets ─────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_allowed():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].pets == "allowed"


def test_parse_pets_not_allowed():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[2].pets == "not_allowed"


# ── floor level ──────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].floor_level == "upper"


def test_parse_floor_level_main():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].floor_level == "main"


def test_parse_floor_level_basement():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[2].floor_level == "basement"


# ── laundry ──────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].laundry_inunit is True


def test_parse_laundry_shared():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].laundry_inunit is False


# ── outdoor space ────────────────────────────────────────────────────────────

def test_parse_outdoor_balcony():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].outdoor_space is True


def test_parse_outdoor_unknown():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].outdoor_space is None


# ── parking ──────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].parking_spots == 2


def test_parse_parking_one_spot():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].parking_spots == 1


# ── utilities ────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[0].utilities == "included"


def test_parse_utilities_extra():
    html = load_fixture("craigslist_hamilton.html")
    result = CraigslistScraper()._parse(html)
    assert result[1].utilities == "extra"


# ── edge cases ───────────────────────────────────────────────────────────────

def test_parse_empty_html_returns_empty_list():
    result = CraigslistScraper()._parse("<html><body></body></html>")
    assert result == []


def test_parse_no_listings_returns_empty_list():
    result = CraigslistScraper()._parse("<html><body><ul></ul></body></html>")
    assert result == []


# ── fetch() ──────────────────────────────────────────────────────────────────

async def test_fetch_calls_fetch_fn():
    html = load_fixture("craigslist_hamilton.html")
    mock_fetch = AsyncMock(return_value=html)
    results = await CraigslistScraper(_fetch=mock_fetch).fetch()

    mock_fetch.assert_called_once()
    assert "hamilton.craigslist.org" in mock_fetch.call_args.args[0]
    assert all(isinstance(r, RawListing) for r in results)
    assert len(results) == 4
