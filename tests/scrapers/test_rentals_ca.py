from pathlib import Path
from unittest.mock import AsyncMock

from rentals_assistant.models import RawListing
from rentals_assistant.scrapers.rentals_ca import RentalsCaScraper, _extract_edges

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _scraper():
    return RentalsCaScraper()


# ── _extract_edges ───────────────────────────────────────────────────────────

def test_extract_edges_from_fixture():
    html = load_fixture("rentals_ca_kitchener.html")
    edges = _extract_edges(html)
    assert len(edges) == 3


def test_extract_edges_returns_empty_for_plain_html():
    assert _extract_edges("<html><body></body></html>") == []


# ── return type ──────────────────────────────────────────────────────────────

def test_parse_returns_list():
    html = load_fixture("rentals_ca_kitchener.html")
    assert isinstance(_scraper()._parse(html, "kitchener"), list)


def test_parse_returns_raw_listing_instances():
    html = load_fixture("rentals_ca_kitchener.html")
    assert all(isinstance(r, RawListing) for r in _scraper()._parse(html, "kitchener"))


def test_parse_returns_three_listings():
    html = load_fixture("rentals_ca_kitchener.html")
    assert len(_scraper()._parse(html, "kitchener")) == 3


# ── required identity fields ────────────────────────────────────────────────

def test_parse_source_is_rentals_ca():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].source == "rentals_ca"


def test_parse_extracts_title():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert "Bright 2BR Upper Unit" in result[0].title


def test_parse_extracts_url():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].url == "https://rentals.ca/kitchener/bright-2br-upper"


def test_parse_extracts_external_id():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].external_id == "111111"


def test_parse_city_from_json():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].city == "kitchener"


# ── price ────────────────────────────────────────────────────────────────────

def test_parse_extracts_price_cad():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].price_cad == 1850


def test_parse_price_third_item():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[2].price_cad == 1950


# ── bedrooms ─────────────────────────────────────────────────────────────────

def test_parse_extracts_bedrooms():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].bedrooms == 2


# ── bathrooms ────────────────────────────────────────────────────────────────

def test_parse_extracts_bathrooms():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[0].bathrooms == 1.0


def test_parse_extracts_bathrooms_half():
    html = load_fixture("rentals_ca_kitchener.html")
    result = _scraper()._parse(html, "kitchener")
    assert result[2].bathrooms == 1.5


# ── fetch() ──────────────────────────────────────────────────────────────────

async def test_fetch_queries_all_cities():
    html = load_fixture("rentals_ca_kitchener.html")
    mock_fetch = AsyncMock(return_value=html)
    await RentalsCaScraper(_fetch=mock_fetch).fetch()

    called_urls = [call.args[0] for call in mock_fetch.call_args_list]
    assert any("kitchener" in u for u in called_urls)
    assert any("waterloo" in u for u in called_urls)
    assert any("cambridge" in u for u in called_urls)


async def test_fetch_aggregates_results_from_all_cities():
    html = load_fixture("rentals_ca_kitchener.html")
    mock_fetch = AsyncMock(return_value=html)
    result = await RentalsCaScraper(_fetch=mock_fetch).fetch()
    assert len(result) == 9  # 3 listings x 3 cities


# ── edge cases ───────────────────────────────────────────────────────────────

def test_parse_empty_html_returns_empty_list():
    result = _scraper()._parse("<html><body></body></html>", "kitchener")
    assert result == []
