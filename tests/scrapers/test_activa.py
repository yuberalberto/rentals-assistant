import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.activa import ActivaScraper

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# -- return type --

def test_parse_returns_list():
    html = load_fixture("activa_rentals.html")
    assert isinstance(ActivaScraper(client=MagicMock())._parse(html), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert all(isinstance(r, RawListing) for r in result)


def test_parse_returns_six_listings():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert len(result) == 6


# -- source / identity --

def test_parse_source_is_activa():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].source == "activa"


def test_parse_extracts_title():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].title == "The Moraine (Garden + Ground Floors)"


def test_parse_extracts_url():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].url == "https://activa.ca/rental/the-moraine-garden-ground-floors/"


def test_parse_extracts_external_id():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].external_id == "the-moraine-garden-ground-floors"


# -- price --

def test_parse_extracts_price_cad():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].price_cad == 2290


# -- bedrooms --

def test_parse_extracts_bedrooms():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].bedrooms == 2


def test_parse_extracts_three_bedrooms():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[5].bedrooms == 3


# -- floor level --

def test_parse_floor_level_garden():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].floor_level == "main"


def test_parse_floor_level_upper():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[2].floor_level == "upper"


# -- parking --

def test_parse_extracts_parking():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].parking_spots == 1


# -- edge cases --

def test_parse_empty_html_returns_empty_list():
    result = ActivaScraper(client=MagicMock())._parse("<html><body></body></html>")
    assert result == []


async def test_fetch_returns_raw_listings():
    mock_response = MagicMock()
    mock_response.text = load_fixture("activa_rentals.html")
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await ActivaScraper(client=mock_client).fetch()
    assert len(result) == 6


def test_parse_logs_warning_when_zero_listings(caplog):
    caplog.set_level(logging.WARNING)
    html = """<html><body>
      <div class="search-filter-results">
        <div class="container">
          <div class="row results-content gx-5"></div>
        </div>
      </div>
    </body></html>"""
    ActivaScraper(client=MagicMock())._parse(html)
    assert "0 listings" in caplog.text


# -- city --

def test_parse_sets_city():
    html = load_fixture("activa_rentals.html")
    result = ActivaScraper(client=MagicMock())._parse(html)
    assert result[0].city is not None
