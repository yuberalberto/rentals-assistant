from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.padmapper import PadMapperScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── return type ───────────────────────────────────────────────────────────────

def test_parse_returns_list():
    html = load_fixture("padmapper_kw.html")
    assert isinstance(PadMapperScraper(client=MagicMock())._parse(html), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert all(isinstance(r, RawListing) for r in result)


def test_parse_returns_three_listings():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert len(result) == 3


# ── source / dedup ────────────────────────────────────────────────────────────

def test_parse_source_is_padmapper_for_direct_listing():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].source == "padmapper"


def test_parse_kijiji_listing_source_is_kijiji():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].source == "kijiji"


def test_parse_kijiji_listing_external_id_from_kijiji_url():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].external_id == "9876543210"


def test_parse_kijiji_listing_url_is_kijiji_canonical():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert "kijiji.ca" in result[1].url


# ── required identity fields ──────────────────────────────────────────────────

def test_parse_extracts_title():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].title == "Bright 2BR Upper Unit - All Utilities Included"


def test_parse_extracts_url_for_direct_listing():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].url == "https://www.padmapper.com/apartments/cambridge-on/bright-upper-unit-pad-001"


def test_parse_extracts_external_id_for_direct_listing():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].external_id == "pad-001"


def test_parse_extracts_city_cambridge():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].city == "cambridge"


def test_parse_extracts_city_kitchener():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].city == "kitchener"


def test_parse_extracts_city_waterloo():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].city == "waterloo"


# ── price ─────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].price_cad == 1850


def test_parse_price_with_plus_utilities_suffix():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].price_cad == 1950


# ── bedrooms ──────────────────────────────────────────────────────────────────

def test_parse_extracts_bedrooms():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].bedrooms == 2


# ── utilities ─────────────────────────────────────────────────────────────────

def test_parse_utilities_included():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].utilities == "included"


def test_parse_utilities_unknown():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].utilities is None


def test_parse_utilities_extra():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].utilities == "extra"


# ── floor level ───────────────────────────────────────────────────────────────

def test_parse_floor_level_upper():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].floor_level == "upper"


def test_parse_floor_level_unknown():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].floor_level is None


def test_parse_floor_level_main():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].floor_level == "main"


# ── pets ──────────────────────────────────────────────────────────────────────

def test_parse_pets_cats_confirmed():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].pets == "cats_confirmed"


def test_parse_pets_not_allowed():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].pets == "not_allowed"


def test_parse_pets_allowed():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].pets == "allowed"


# ── laundry ───────────────────────────────────────────────────────────────────

def test_parse_laundry_inunit_from_insuite():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].laundry_inunit is True


def test_parse_laundry_unknown():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].laundry_inunit is None


def test_parse_laundry_inunit_from_inunit_keyword():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].laundry_inunit is True


# ── outdoor space ─────────────────────────────────────────────────────────────

def test_parse_outdoor_space_balcony():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].outdoor_space is True


def test_parse_outdoor_space_unknown():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].outdoor_space is None


def test_parse_outdoor_space_yard():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].outdoor_space is True


# ── parking ───────────────────────────────────────────────────────────────────

def test_parse_parking_two_spots():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[0].parking_spots == 2


def test_parse_parking_unknown():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[1].parking_spots is None


def test_parse_parking_one_spot():
    html = load_fixture("padmapper_kw.html")
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result[2].parking_spots == 1


# ── edge cases ────────────────────────────────────────────────────────────────

def test_parse_skips_card_without_link():
    html = """<html><body>
      <ul class="listings-list">
        <li class="listing-card" data-id="999">
          <span class="listing-card__title">No link here</span>
        </li>
      </ul>
    </body></html>"""
    result = PadMapperScraper(client=MagicMock())._parse(html)
    assert result == []


def test_parse_empty_html_returns_empty_list():
    result = PadMapperScraper(client=MagicMock())._parse("<html><body></body></html>")
    assert result == []


# ── fetch() ───────────────────────────────────────────────────────────────────

async def test_fetch_makes_single_request():
    mock_response = MagicMock()
    mock_response.text = load_fixture("padmapper_kw.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    await PadMapperScraper(client=mock_client).fetch()

    assert mock_client.get.call_count == 1


async def test_fetch_returns_raw_listings():
    mock_response = MagicMock()
    mock_response.text = load_fixture("padmapper_kw.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await PadMapperScraper(client=mock_client).fetch()

    assert len(result) == 3
